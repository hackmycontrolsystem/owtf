"""
owtf.scanner.service
~~~~~~~~~~~~~~~~~~~
The scan_network scans the network for different ports and call network plugins for different services running on target
"""

import re
import logging

from owtf.utils.file import FileOperations
from owtf.
SCANS_FOLDER = "scans"  # Folder under which all scans will be saved
PING_SWEEP_FILE = "%s/00_ping_sweep" % SCANS_FOLDER
DNS_INFO_FILE = "%s/01_dns_info" % SCANS_FOLDER
FAST_SCAN_FILE = "%s/02_fast_scan" % SCANS_FOLDER
STD_SCAN_FILE = "%s/03_std_scan" % SCANS_FOLDER
FULL_SCAN_FILE = "%s/04_full_scan" % SCANS_FOLDER

logger = logging.getLogger(__name__)


def ping_sweep(target, scantype):
    """Do a ping sweep

    :param target: Target to scan
    :type target: `str`
    :param scantype: Type of scan
    :type scantype: `str`
    :return: None
    :rtype: None
    """
    if scantype == "full":
        logging.info("Performing Intense Host discovery")
        shell.shell_exec("nmap -n -v -sP -PE -PP -PS21,22,23,25,80,443,113,21339 -PA80,113,443,10042"
                         " --source_port 53 %s -oA %s" % (target, PING_SWEEP_FILE))

    if scantype == "arp":
        logging.info("Performing ARP host discovery")
        shell.shell_exec("nmap -n -v -sP -PR %s -oA %s" %
                         (target, PING_SWEEP_FILE))

    shell.shell_exec('grep Up %s.gnmap | cut -f2 -d\" \" > %s.ips' %
                     (PING_SWEEP_FILE, PING_SWEEP_FILE))


def dns_sweep(file_with_ips, file_prefix):
    """Do a DNS sweep

    :param file_with_ips: Path of file with IP addresses
    :type file_with_ips: `str`
    :param file_prefix: File name prefix
    :type file_prefix: `str`
    :return: None
    :rtype: None
    """
    logging.info(
        "Finding misconfigured DNS servers that might allow zone transfers among live ips ..")
    shell.shell_exec("nmap -PN -n -sS -p 53 -iL %s -oA %s" %
                     (file_with_ips, file_prefix))

    # Step 2 - Extract IPs
    dns_servers = "%s.dns_server.ips" % file_prefix
    shell.shell_exec('grep \"53/open/tcp\" %s.gnmap | cut -f 2 -d \" \" > %s' %
                     (file_prefix, dns_servers))
    file = FileOperations.open(dns_servers)
    domain_names = "%s.domain_names" % file_prefix
    shell.shell_exec("rm -f %s" % domain_names)
    num_dns_servers = 0
    for line in file:
        if line.strip('\n'):
            dns_server = line.strip('\n')
            shell.shell_exec("host %s %s | grep 'domain name' | cut -f 5 -d' ' | cut -f 2,3,4,5,6,7 -d. "
                             "| sed 's/\.$//' >> %s" % (dns_server, dns_server, domain_names))
            num_dns_servers += 1
    try:
        file = FileOperations.open(domain_names, owtf_clean=False)
    except IOError:
        return

    for line in file:
        domain = line.strip('\n')
        raw_axfr = "%s.%s.%s.axfr.raw" % (file_prefix, dns_server, domain)
        shell.shell_exec("host -l %s %s | grep %s > %s" %
                         (domain, dns_server, domain, raw_axfr))
        success = shell.shell_exec("wc -l %s | cut -f 1  -d ' '" % raw_axfr)
        if success > 3:
            logging.info(
                "Attempting zone transfer on $dns_server using domain %s.. Success!" % domain)
            axfr = "%s.%s.%s.axfr" % (file_prefix, dns_server, domain)
            shell.shell_exec("rm -f %s" % axfr)
            logging.info(shell.shell_exec("grep 'has address' %s | cut -f 1,4 -d ' ' | sort -k 2 -t ' ' "
                                          "| sed 's/ /#/g'" % raw_axfr))
        else:
            logging.info(
                "Attempting zone transfer on $dns_server using domain %s.. Success!" % domain)
            shell.shell_exec("rm -f %s" % raw_axfr)
    if num_dns_servers == 0:
        return


def scan_and_grab_banners(file_with_ips, file_prefix, scan_type, nmap_options):
    """Scan targets and grab service banners

    :param file_with_ips: Path to file with IPs
    :type file_with_ips: `str`
    :param file_prefix: File name prefix
    :type file_prefix: `str`
    :param scan_type: Type of scan
    :type scan_type: `str`
    :param nmap_options: nmap options
    :type nmap_options: `dict`
    :return: None
    :rtype: None
    """
    if scan_type == "tcp":
        logging.info(
            "Performing TCP portscan, OS detection, Service detection, banner grabbing, etc")
        shell.shell_exec("nmap -PN -n -v --min-parallelism=10 -iL %s -sS -sV -O  -oA %s.tcp %s") % (
            file_with_ips, file_prefix, nmap_options)
        shell.shell_exec("amap -1 -i %s.tcp.gnmap -Abq -m -o %s.tcp.amap -t 90 -T 90 -c 64" % (file_prefix,
                                                                                               file_prefix))

    if scan_type == "udp":
            logging.info(
                "Performing UDP portscan, Service detection, banner grabbing, etc")
            shell.shell_exec("nmap -PN -n -v --min-parallelism=10 -iL %s -sU -sV -O -oA %s.udp %s" % (
                file_with_ips, file_prefix, nmap_options))
            shell.shell_exec(
                "amap -1 -i %s.udp.gnmap -Abq -m -o %s.udp.amap" % (file_prefix, file_prefix))


def get_nmap_services_file(self):
    """Return default NMAP services file

    :return: Path to the file
    :rtype: `str`
    """
    return '/usr/share/nmap/nmap-services'


def get_ports_for_service(service, protocol):
    """Get ports for different services

    :param service: Service name
    :type service: `str`
    :param protocol: Protocol
    :type protocol: `str`
    :return: List of ports
    :rtype: `list`
    """
    regexp = '(.*?)\t(.*?/.*?)\t(.*?)($|\t)(#.*){0,1}'
    re.compile(regexp)
    list = []
    f = FileOperations.open(get_nmap_services_file())
    for line in f.readlines():
        if line.lower().find(service) >= 0:
            match = re.findall(regexp, line)
            if match:
                port = match[0][1].split('/')[0]
                prot = match[0][1].split('/')[1]
                if (not protocol or protocol == prot) and port not in list:
                    list.append(port)
    f.close()
    return list


def target_service(nmap_file, service):
    """Services for a target

    :param nmap_file: Path to nmap file
    :type nmap_file: `str`
    :param service: Service to get
    :type service: `str`
    :return: Response
    :rtype: `str`
    """
    ports_for_service = get_ports_for_service(service, "")
    f = FileOperations.open(nmap_file.strip())
    response = ""
    for host_ports in re.findall('Host: (.*?)\tPorts: (.*?)[\t\n]', f.read()):
        host = host_ports[0].split(' ')[0]  # Remove junk at the end
        ports = host_ports[1].split(',')
        for port_info in ports:
            if len(port_info) < 1:
                continue
            chunk = port_info.split('/')
            port = chunk[0].strip()
            port_state = chunk[1].strip()
            # No point in wasting time probing closed/filtered ports!!
            # (nmap sometimes adds these to the gnmap file for some reason ..)
            if port_state in ['closed', 'filtered']:
                continue
            try:
                prot = chunk[2].strip()
            except:
                continue
            if port in ports_for_service:
                response += "%s:%s:%s##" % (host, port, prot)
    f.close()
    return response


def probe_service_for_hosts(nmap_file, target):
    """Probe a service for a domain

    :param nmap_file: Path to nmap file
    :type nmap_file: `str`
    :param target: Target name
    :type target: `str`
    :return: List of services
    :rtype: `list`
    """
    services = []
    # Get all available plugins from network plugin order file
    net_plugins = config.Plugin.GetOrder("network")
    for plugin in net_plugins:
        services.append(plugin['Name'])
    services.append("http")
    total_tasks = 0
    tasklist = ""
    plugin_list = []
    http = []
    for service in services:
        if plugin_list.count(service) > 0:
            continue
        tasks_for_service = len(target_service(
            nmap_file, service).split("##")) - 1
        total_tasks += tasks_for_service
        tasklist = "%s [ %s - %s tasks ]" % (tasklist,
                                             service, str(tasks_for_service))
        for line in target_service(nmap_file, service).split("##"):
            if line.strip("\n"):
                ip = line.split(":")[0]
                port = line.split(":")[1]
                plugin_to_invoke = service
                service1 = plugin_to_invoke
                config.Set("%s_PORT_NUMBER" % service1.upper(), port)
                if service != 'http':
                    plugin_list.append(plugin_to_invoke)
                    http.append(port)
                logging.info("We have to probe %s:%s for service %s",
                             str(ip), str(port), plugin_to_invoke)
    return http


def scan_network(target):
    """Do a ping sweep for a target

    :param target: Target url
    :type target: `str`
    :return: None
    :rtype: None
    """
    ping_sweep(target.split("//")[1], "full")
    dns_sweep("%s.ips" % PING_SWEEP_FILE, DNS_INFO_FILE)


def probe_network(target, protocol, port):
    """Probe network for services

    :param target: target url
    :type target: `str`
    :param protocol: Protocol scan
    :type protocol: `str`
    :param port: Port number for target
    :type port: `int`
    :return: None
    :rtype: None
    """
    scan_and_grab_banners("%s.ips" % PING_SWEEP_FILE,
                          FAST_SCAN_FILE, protocol, "-p %s" % port)
    return probe_service_for_hosts("%s.%s.gnmap" % (FAST_SCAN_FILE, protocol), target.split("//")[1])