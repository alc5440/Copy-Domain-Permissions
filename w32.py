"""
Module: w32.py
Description: Uses Win32 API to resolve/get SIDs and get users

Author: Andrew Collings
Created: 2025-02-08
Updated: 2025-02-11
License: MIT
"""

import win32api, win32security, win32net, win32netcon
import sys
import questionary

computer_name = win32api.GetComputerName()

def resolve_sids(sids):
    print("Resolve SIDs to accounts")
    resolved_sids = []
    for sid in sids:
        bin_sid = win32security.GetBinarySid(sid)
        try:
            account = win32security.LookupAccountSid(computer_name, bin_sid)
        except:
            account = False
        user_line = [sid, bin_sid]
        if not account:
            user_line.append(account)
        else:
            user_line.extend(account)
        resolved_sids.append(user_line)
    return resolved_sids

def get_users(level, server):
    resume = 0
    users = []
    while True:
        try:
            user_list, total, resume = win32net.NetUserEnum(server, level, win32netcon.FILTER_NORMAL_ACCOUNT, resume)
            users.extend(user_list)
            if resume == 0:
                break
        except Exception as e:
            print(f"Error fetching user list: {e}")
            break
    return users

def get_groups(level, server):
    resume = 0
    groups = []
    while True:
        try:
            group_list, total, resume = win32net.NetGroupEnum(server, level, resume)
            groups.extend(group_list)
            if resume == 0:
                break
        except Exception as e:
            print(f"Error fetching user list: {e}")
            break
    return groups

def get_domain_users(dc_fqdns):
    print("Enumerate all users")
    domain_users = {}
    user_level = 2
    for domain, fqdn in dc_fqdns.items():
        users = get_users(user_level, fqdn[0])
        domain_users.update({domain:users})
    return domain_users

def skip_disabled(filtered_users, domain_users, template_domain):
    active_users = []
    disabled_users = []
    for i in range(len(filtered_users)):
        for j in domain_users[template_domain]:
            if j['name'] == filtered_users[i][2]:
                if not bool(j['flags'] & win32netcon.UF_ACCOUNTDISABLE):
                    active_users.append(filtered_users[i])
                    break
                if bool(j['flags'] & win32netcon.UF_ACCOUNTDISABLE):
                    disabled_users.append(filtered_users[i])
                    break
                else:
                    print(f'Error determining if user {j['full_name']} ({j['name']}) is disabled. Exiting...')
                    sys.exit()
    print("The following users are disabled and will not be mapped to users in the target domain:")
    for i in range(len(disabled_users)):
        print(f'{disabled_users[i][2]}', end='   ')
        if (i + 1) % 5 == 0:
            print()
    user_proceed = questionary.confirm('Do you want to continue?').ask()
    if not user_proceed:
        sys.exit()
    else:
        return active_users, disabled_users

def get_user_sid(matched_users):
    for i in range(len(matched_users)):
        sid_object = win32security.LookupAccountName(computer_name, matched_users[i][7])
        matched_users[i].append(win32security.ConvertSidToStringSid(sid_object[0]))
    return matched_users