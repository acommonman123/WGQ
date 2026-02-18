from re import L


with open('/home/wspn02/mega/WGQ/convergence_test/arrived_pkts.txt', 'r') as f:
    lines = f.read()
    lines.strip()
    lines = lines.split('\n')
    lines.pop()
    for i in range(len(lines)):
        lines[i] = float(lines[i])
    print(lines)
    average_delay = sum(lines) / len(lines)
    print("Average Delay: ", average_delay)
        