import argparse # parse command-line argument
import dns.message #constructs and parses DNS messages
import dns.query #executes dns queries using transport protocols(UDP, TCP)
import dns.name #handles dns names provides classes and functions to manipulate
import dns.rdata #provides class for dns resource data
import dns.rdataclass # provides constants for dns resource record class like internet
import dns.rdatatype # provides constants for dns resource record types

#dns records in human readable format
#(dns record type, format string)
RECORDS=(("CNAME", "{alias} is an alias for {name}"), # canonical name , alias for the name
         ("A", "{name} has address {address}"), # maps domain name to IPv4 address 
         ("AAAA", "{name} has IPv6 address"), # internet transitions to IPv6
         ("MX", "{name} mail is handled by {perference}{exchange}") # direct email to the correct mail servers
         ) 

#cname-pointing multiple domains names to the same ip address or alias subdomans to another domain name 
#a-essential for translating domain names to ip addresses that computers use to identify each other on the network
#aaaa-used as the internet transitions from IPv4 to IPv6, which allows for a much larger number of unique IP addresses compared to IPv4
#mx-direct email to the correct mail servers, priority value (lower means higher priority) determines the order in which mail servers are tried if multiple MX records exist

ROOT_SERVERS = ("198.41.0.4",
                "199.9.14.201",
                "192.33.4.12",
                "199.7.91.13",
                "192.203.230.10",
                "192.5.5.241",
                "192.112.36.4",
                "198.97.190.53",
                "192.36.148.17",
                "192.58.128.30",
                "193.0.14.129",
                "199.7.83.42",
                "202.12.27.33"
                )

simple_cache = {}
sophis_cache = {}

def collect_results(name: str) -> dict:
    """
    This function parses final answers into the proper data structure that
    print_results requires. The main work is done within the lookup function.
    """
    if name in simple_cache:
        return simple_cache[name]
    
    full_response = {}
    target_name = dns.name.from_text(name)
    
    for rtype, fmt_str in RECORDS:
        response = lookup(target_name, dns.rdatatype.from_text(rtype))
        records = []
        
        if response and hasattr(response, 'answer') and response.answer:
            for answers in response.answer:
                a_name = answers.name
                for answer in answers:
                    if rtype == "MX":
                        records.append({
                            "name": a_name,
                            "preference": answer.preference,
                            "exchange": str(answer.exchange)
                        })
                    else:
                        records.append({
                            "name": a_name,
                            "address": str(answer)
                        })
        
        full_response[rtype] = records
    
    simple_cache[name] = full_response
    return full_response

def lookup(target_name: dns.name.Name,
           qtype: dns.rdata.Rdata) -> dns.message.Message:
    """
    This function uses a recursive resolver to find the relevant answer to the
    query.
    """
    split = str(target_name).split(".")
    domain = ".".join(split[-2:]) # includes subdomains
    if domain not in sophis_cache:
        sophis_cache[domain] = {}
    response = None
    for r_server in ROOT_SERVERS:
        if r_server in sophis_cache[domain]:
            response = sophis_cache[domain][r_server]
        else:
            response = queryServer(target_name, qtype, r_server)
            sophis_cache[domain][r_server] = response
        if response:
            if response.answer:
                return response
            elif response.additional:
                for additional in response.additional:
                    if additional.rdtype != 1:
                        continue
                    for add in additional:
                        new_response = lookupRecursive(target_name,
                                                       qtype, str(add))
                        if new_response:
                            return new_response
    return None

def queryServer(target_name: dns.name.Name,
                qtype: dns.rdata.Rdata, ipAddr: str) -> dns.message.Message:
    """
    Makes a udp query to a given ip address, takes care of exceptions
    """
    outbound_query = dns.message.make_query(target_name, qtype)
    response = None
    try:
        response = dns.query.udp(outbound_query, ipAddr, 3)
    except Exception as e:
        response = None
    return response

def lookupRecursive(target_name: dns.name.Name,
                    qtype: dns.rdata.Rdata,
                    ipAddr: str) -> dns.message.Message:
    """
    Recursive lookup that starts from TLD and goes to the lowest level
    """
    response = queryServer(target_name, qtype, ipAddr)
    if response:
        if response.answer:
            for answer in response.answer:
                if answer.rdtype == 5 and qtype != 5:
                    target_name = dns.name.from_text(str(answer[0]))
                    return lookup(target_name, qtype)
            return response
        elif response.additional:
            for additional in response.additional:
                if additional.rdtype != 1:
                    continue
                for add in additional:
                    ip = str(add)
                    new_response = lookupRecursive(target_name, qtype, ip)
                    if new_response:
                        return new_response
    return response

def print_results(results: dict) -> None:
    """
    take the results of a lookup and print them to the screen like the host
    program would.
    """
    for rtype, fmt_str in RECORDS:
        for result in results.get(rtype, []):
            print(fmt_str.format(**result))
            
def main():
    """
    if run from the command line, take args and call
    printresults(lookup(hostname))
    """
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("name", nargs="+",
                                 help="DNS name(s) to look up")
    argument_parser.add_argument("-v", "--verbose",
                                 help="increase output verbosity",
                                 action="store_true")
    program_args = argument_parser.parse_args()
    for a_domain_name in program_args.name:
        result = collect_results(a_domain_name)
        if (result != -1):
            print_results(result)
            
def dns_to_ip(domain_name: str) -> str:
    """
    Resolves a domain name to its corresponding IP address using the DNS resolution logic.
    """
    result = collect_results(domain_name)
    
    # Assuming you want to extract the IPv4 address (A record) if available
    a_records = result.get("A", [])
    if a_records:
        return a_records[0]["address"]
    
    # If there are no A records, you can handle the case accordingly
    return "No A records found for the given domain."