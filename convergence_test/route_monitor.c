// route_monitor.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <time.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>

#define LOG_FILE    "/files/time.txt"
#define LOG_DIR     "/files"
#define LOCK_FILE   "/run/route_monitor.lock"
#define RECV_BUFSZ  (32 * 1024)

#define DEDUP_SAME_SECOND 1   // 1=同一秒内只写一次；0=每条事件都写

static volatile sig_atomic_t g_stop = 0;
static int g_nl_fd = -1;

static char g_container_id[128] = {0};

/* ---------- 获取容器标识 ---------- */
/*
 * 优先级：
 *  1) 环境变量 ROUTE_MONITOR_ID（你可以在 docker/k8s 启动时显式设置）
 *  2) 环境变量 HOSTNAME（很多容器默认就是容器ID/Pod名）
 *  3) gethostname()
 */
static void init_container_id(void) {
    const char *id = getenv("ROUTE_MONITOR_ID");
    if (!id || !*id) id = getenv("HOSTNAME");

    if (id && *id) {
        snprintf(g_container_id, sizeof(g_container_id), "%s", id);
    } else {
        if (gethostname(g_container_id, sizeof(g_container_id) - 1) != 0) {
            snprintf(g_container_id, sizeof(g_container_id), "unknown");
        }
        g_container_id[sizeof(g_container_id) - 1] = '\0';
    }

    // 简单清理：把空白替换成 _
    for (size_t i = 0; i < strlen(g_container_id); i++) {
        if (g_container_id[i] == ' ' || g_container_id[i] == '\t' ||
            g_container_id[i] == '\n' || g_container_id[i] == '\r') {
            g_container_id[i] = '_';
        }
    }
}

/* ---------- 信号处理：可被 Ctrl+C / pkill 正常终止 ---------- */
static void on_signal(int sig) {
    (void)sig;
    g_stop = 1;

    // 关键：close 阻塞的 netlink fd，确保 recvmsg 立刻返回
    if (g_nl_fd >= 0) {
        close(g_nl_fd);
        g_nl_fd = -1;
    }
}

static int setup_signal_handlers(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_signal;
    sigemptyset(&sa.sa_mask);

    // 不要 SA_RESTART，避免 recvmsg 自动重启导致退出不及时
    sa.sa_flags = 0;

    if (sigaction(SIGINT,  &sa, NULL) < 0) { perror("sigaction(SIGINT)");  return -1; }
    if (sigaction(SIGTERM, &sa, NULL) < 0) { perror("sigaction(SIGTERM)"); return -1; }
    if (sigaction(SIGHUP,  &sa, NULL) < 0) { perror("sigaction(SIGHUP)");  return -1; }
    if (sigaction(SIGQUIT, &sa, NULL) < 0) { perror("sigaction(SIGQUIT)"); return -1; }
    return 0;
}

/* ---------- 确保日志目录存在 ---------- */
static void ensure_log_dir(void) {
    if (mkdir(LOG_DIR, 0775) < 0) {
        if (errno != EEXIST) perror("mkdir " LOG_DIR);
    }
}

/* ---------- 单实例锁（容器内单实例；锁文件放 /run） ---------- */
static int acquire_single_instance_lock(void) {
    int fd = open(LOCK_FILE, O_CREAT | O_RDWR, 0664);
    if (fd < 0) {
        perror("open lock file");
        return -1;
    }
    if (flock(fd, LOCK_EX | LOCK_NB) < 0) {
        fprintf(stderr, "route_monitor already running (lock: %s)\n", LOCK_FILE);
        close(fd);
        return -1;
    }
    // 不要 close(fd)，保持锁有效
    return fd;
}

/* ---------- 写日志：<ts> <container_id>\n ---------- */
static void log_ts_with_id(time_t ts) {
    int fd = open(LOG_FILE, O_WRONLY | O_CREAT | O_APPEND, 0664);
    if (fd < 0) { perror("open log"); return; }

    // 如果多个容器共享同一个 /files/time.txt，建议加 flock 防止行交错
    if (flock(fd, LOCK_EX) < 0) {
        // flock 失败也继续写（不致命）
    }

    char line[256];
    int n = snprintf(line, sizeof(line), "%ld %s\n", (long)ts, g_container_id);
    if (n > 0) {
        // 单次 write，尽量保证原子性
        (void)write(fd, line, (size_t)n);
    }

    (void)flock(fd, LOCK_UN);
    close(fd);
}

/* ---------- 创建并绑定 Netlink socket，订阅路由变更 ---------- */
static int open_route_nl_socket(void) {
    int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    if (fd < 0) { perror("socket(AF_NETLINK)"); return -1; }

    int rcvbuf = 4 * 1024 * 1024;
    (void)setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf));

    struct sockaddr_nl sa;
    memset(&sa, 0, sizeof(sa));
    sa.nl_family = AF_NETLINK;
    sa.nl_pid    = (uint32_t)getpid();
    sa.nl_groups = RTMGRP_IPV4_ROUTE | RTMGRP_IPV6_ROUTE;

    if (bind(fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        perror("bind(AF_NETLINK)");
        close(fd);
        return -1;
    }
    return fd;
}

/* ---------- 处理一次 recvmsg 得到的 netlink 消息 ---------- */
static void handle_nl_messages(char *buf, ssize_t len, time_t *last_logged_ts) {
    struct nlmsghdr *nh;
    for (nh = (struct nlmsghdr *)buf; NLMSG_OK(nh, (unsigned int)len);
         nh = NLMSG_NEXT(nh, len)) {

        if (nh->nlmsg_type == NLMSG_DONE) return;

        if (nh->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nh);
            if (nh->nlmsg_len >= NLMSG_LENGTH(sizeof(struct nlmsgerr))) {
                fprintf(stderr, "netlink error: %s\n",
                        err->error ? strerror(-err->error) : "unknown");
            } else {
                fprintf(stderr, "netlink error: (truncated)\n");
            }
            return;
        }

        if (nh->nlmsg_type == RTM_NEWROUTE || nh->nlmsg_type == RTM_DELROUTE) {
            time_t now = time(NULL);

#if DEDUP_SAME_SECOND
            if (last_logged_ts && now == *last_logged_ts) continue;
            if (last_logged_ts) *last_logged_ts = now;
#endif
            log_ts_with_id(now);
        }
    }
}

int main(void) {
    if (setup_signal_handlers() < 0) return 1;

    init_container_id();
    ensure_log_dir();

    int lockfd = acquire_single_instance_lock();
    if (lockfd < 0) return 1;

    g_nl_fd = open_route_nl_socket();
    if (g_nl_fd < 0) return 1;

    char buf[RECV_BUFSZ];
    time_t last_logged_ts = 0;

    while (!g_stop) {
        struct sockaddr_nl nladdr;
        struct iovec iov = { .iov_base = buf, .iov_len = sizeof(buf) };
        struct msghdr msg;
        memset(&msg, 0, sizeof(msg));
        msg.msg_name    = &nladdr;
        msg.msg_namelen = sizeof(nladdr);
        msg.msg_iov     = &iov;
        msg.msg_iovlen  = 1;

        ssize_t n = recvmsg(g_nl_fd, &msg, 0);
        if (n < 0) {
            if (g_stop) break;
            if (errno == EINTR) continue;
            perror("recvmsg");
            break;
        }

        handle_nl_messages(buf, n, &last_logged_ts);
    }

    if (g_nl_fd >= 0) close(g_nl_fd);
    close(lockfd);
    return 0;
}

