"""
Module: ldap.py
Description: Pulls group data from LDAP

Author: Andrew Collings
Created: 2025-02-08
Updated: 2025-02-11
License: MIT
"""

from ldap3 import Server, Connection, NTLM, SUBTREE

def get_groups(dc_fqns):
    print('Getting groups from LDAP')
    domain_groups = {}
    group_filter = '(objectClass=group)'
    attributes = ["cn", "distinguishedName", 'objectSid']  # Adjust attributes as needed
    for domain in dc_fqns:
        ldap_server = f"ldap://{dc_fqns[domain][0]}"
        base_dn = f"dc={domain.lower()},dc={dc_fqns[domain][0].split('.')[-1]}"
        server = Server(ldap_server,port= 389)
        conn = Connection(server, user=f'{domain.lower()}\\{dc_fqns[domain][1]}', password=dc_fqns[domain][2], authentication=NTLM, auto_bind=True)
        conn.search(search_base=base_dn, search_filter=group_filter, search_scope=SUBTREE, attributes=attributes)
        domain_groups.update({domain: {entry.objectSid.value: entry.cn.value for entry in conn.entries}})
        conn.unbind()
    return domain_groups