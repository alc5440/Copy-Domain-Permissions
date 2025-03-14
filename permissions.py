"""
Script: permissions.py
Description: Replicate permissions from one domain to another using text files from/to icacls

Usage:
    python permissions.py <icacls export file>

Modules:
    - parse.py: Parses data for use by other functions
    - correlate.py: Correlates objects between domains
    - ldap.py: Connects via LDAP to pull groups
    - w32.py: Uses Win32 API to resolve/get SIDs and get users

Author: Andrew Collings
Created: 2025-01-16
Updated: 2025-02-11
License: MIT
"""

import multiprocessing
import questionary
import sys, os
import getpass
import parse, w32, ldap, correlate


if __name__ == "__main__":

    num_workers = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(num_workers)

    def load_file():
        print("Load File")
        with open(sys.argv[1], "r", encoding="utf-16-le") as acl_file:
            file_lines = [line.lstrip("\ufeff").strip() for line in acl_file]
        return file_lines

    def get_dom_creds(unique_domains):
        dc_fqdns = {}
        for domain in sorted(unique_domains):
            fqdn = input(f"Please enter the DC FQDN for the domain {domain}: ")
            dom_admin = input(f"Please enter a domain admin username for the domain {domain}: ")
            admin_pass = getpass.getpass(f"Please enter the password for {dom_admin}: ")
            dc_fqdns.update({domain:[fqdn, dom_admin, admin_pass]})
        return dc_fqdns
        
    #Load file
    try:
        file_lines = load_file()
    except:
        print('Please launch the script with an icacls export file (relative to your current path) as an argument.')
        exit()
    chunked_lines, chunk_size = parse.build_chunk(file_lines, num_workers)
    chunked_files = parse.isolate_permissions(chunked_lines, pool, chunk_size)

    #Isolate SIDs
    sids = parse.find_unique_sids(chunked_files, pool)
    first_pass_sids = w32.resolve_sids(sids)
    unique_domains = parse.identify_domains(first_pass_sids)
    print('The following domains have been identified from the permission file:')
    print(''.join(f'{i}   ' for i in unique_domains), end='')
    manual_target_domain = input('\nPlease enter the NetBIOS name for the target domain if not listed above (otherwise leave blank) then hit Enter: ').upper()
    if manual_target_domain: unique_domains.add(manual_target_domain)

    #Domain details
    dc_fqdns = get_dom_creds(unique_domains)
    domain_choices = list(dc_fqdns.keys())
    template_domain = questionary.select("Please select the domain to use as a permission template: ", domain_choices).ask()
    domain_choices.remove(template_domain)
    target_domain = questionary.select("Please select the target domain to add permission: ", domain_choices).ask()

    #Get users and groups
    domain_users = w32.get_domain_users(dc_fqdns)
    domain_groups = ldap.get_groups(dc_fqdns)

    #Resolve SIDs
    resolved_sids, unresolved_sids = parse.separate_unresolved(first_pass_sids)
    resolved_groups, still_unresolved = parse.second_pass_resolve(unresolved_sids, domain_groups)
    if resolved_groups:
        resolved_sids += resolved_groups
    
    identified_users, identified_groups = parse.separate_users_groups(resolved_sids)
    
    #Correlate users
    filtered_users = [user for user in identified_users if user[3] == template_domain]
    skip_disabled_users = questionary.confirm('Would you like to skip matching disabled users?').ask()
    if skip_disabled_users:
        filtered_users, disabled_users = w32.skip_disabled(filtered_users, domain_users, template_domain)
    matched_users = correlate.users(filtered_users, domain_users, template_domain, target_domain)
    matched_users_sids = w32.get_user_sid(matched_users)

    #Correlate groups
    filtered_groups = [group for group in identified_groups if group[3] == template_domain]
    matched_groups = correlate.groups(filtered_groups, domain_groups, target_domain)
    
    #Pair SIDs
    print('Pairing SIDs')
    paired_sids = parse.make_sid_pairs(matched_users, matched_groups)

    #Write new permissions
    new_perms = parse.match_perms(chunked_files, paired_sids, pool)
    pool.close()
    pool.join()
    print(f'The output file will be created in your current working directory which is:\n{os.getcwd()}')
    file_name = input('Please enter a filename for the output: ')
    with open(file_name, "w", encoding="utf-16-le") as new_acl_file:
        new_acl_file.write('\ufeff')
        for chunk in new_perms:
                new_acl_file.writelines(chunk)
    print('Done! Please use icacls restore to apply.')
