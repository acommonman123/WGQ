// route_cnt_watch.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <arpa/inet.h>
#include <time.h>
#include <errno.h>

#define LOG_FILE  "/files/time.txt"
#define INTERVAL  1          /* 秒 */

/* ---------- 写时间戳 ---------- */
void log_ts(void)
{
    int fd = open(LOG_FILE, O_WRONLY | O_CREAT | O_APPEND, 0664);
    if (fd < 0) { perror("open log"); return; }
    dprintf(fd, "%ld\n", (long)time(NULL));
    close(fd);
}

/* ---------- 发送 Netlink 请求 ---------- */
int nl_request_dump(int family)
{
    int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    if (fd < 0) { perror("socket"); return -1; }

    struct sockaddr_nl sa = { .nl_family = AF_NETLINK };
    if (bind(fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        perror("bind"); close(fd); return -1;
    }

    char req[256];
    struct nlmsghdr *nh = (struct nlmsghdr *)req;
    struct rtmsg        *rt;

    nh->nlmsg_len    = NLMSG_LENGTH(sizeof(struct rtmsg));
    nh->nlmsg_type   = RTM_GETROUTE;
    nh->nlmsg_flags  = NLM_F_REQUEST | NLM_F_DUMP;
    rt               = NLMSG_DATA(nh);
    memset(rt, 0, sizeof(*rt));
    rt->rtm_family   = family;          /* AF_INET or AF_INET6 */

    if (send(fd, nh, nh->nlmsg_len, 0) < 0) {
        perror("send"); close(fd); return -1;
    }
    return fd;   /* 调用者负责关闭 */
}

/* ---------- 接收并计数 ---------- */
size_t count_routes(int family)
{
    int fd = nl_request_dump(family);
    if (fd < 0) return 0;

    size_t cnt = 0;
    char   buf[16 * 1024];
    struct sockaddr_nl nladdr;
    struct iovec iov = { buf, sizeof(buf) };
    struct msghdr msg = {
        .msg_name = &nladdr,
        .msg_namelen = sizeof(nladdr),
        .msg_iov = &iov,
        .msg_iovlen = 1,
    };

    while (1) {
        ssize_t len = recvmsg(fd, &msg, 0);
        if (len < 0) { perror("recvmsg"); break; }

        struct nlmsghdr *nh;
        for (nh = (struct nlmsghdr *)buf; NLMSG_OK(nh, len);
             nh = NLMSG_NEXT(nh, len)) {
            if (nh->nlmsg_type == RTM_NEWROUTE)
                ++cnt;
            if (nh->nlmsg_type == NLMSG_DONE)
                goto out;
            if (nh->nlmsg_type == NLMSG_ERROR) {
                fprintf(stderr, "nl error\n");
                goto out;
            }
        }
    }
out:
    close(fd);
    return cnt;
}

/* ---------- main ---------- */
int main(void)
{
    system("mkdir -p $(dirname " LOG_FILE ")");
    size_t prev4 = 0, prev6 = 0, curr4, curr6;

    for (;;) {
        curr4 = count_routes(AF_INET);
        curr6 = count_routes(AF_INET6);
        if (curr4 != prev4 || curr6 != prev6) {
            log_ts();
            prev4 = curr4;
            prev6 = curr6;
        }
        sleep(INTERVAL);
    }
    return 0;
}
