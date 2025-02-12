"""
Module: parse.py
Description: Parses data for use by other functions

Author: Andrew Collings
Created: 2025-02-08
Updated: 2025-02-11
License: MIT
"""

import itertools

def chunkify(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]

def process_chunk_lines(chunk):
    chunk_file_list = []
    for line in chunk:
        sacl = ''
        pline = line[1]
        if 'S:' in line[1]:
            sacl_split = pline.split('S:')
            sacl = 'S:' + sacl_split[1]
            pline = sacl_split[0]
        fperms = pline.split('(')
        file_permissions = []
        for i in fperms[1:]:
            file_permissions.append('(' + i)
        file_line = [line[0], fperms[0], file_permissions, sacl]
        chunk_file_list.append(file_line)
    return chunk_file_list

def process_sids(file_chunk):
    sid_chunk = set()
    for file in file_chunk:
        for perm in file[2]:
            sid = perm.split(';;;')[1][:-1]
            if sid.startswith('S-1-5-21-'):
                sid_chunk.add(sid)
    return sid_chunk

def build_chunk(file_lines, num_workers):
    print("Build and chunk list")
    paired_lines = [list(pair) for pair in itertools.zip_longest(*[iter(file_lines)]*2, fillvalue=None)]
    chunk_size = len(paired_lines) // num_workers
    chunked_lines = list(chunkify(paired_lines, chunk_size))
    return chunked_lines, chunk_size

def isolate_permissions(chunked_lines, pool, chunk_size):
    print("Isolate permissions")
    file_list_chunks = pool.map(process_chunk_lines, chunked_lines)
    file_list = [item for sublist in file_list_chunks for item in sublist]
    chunked_files = list(chunkify(file_list, chunk_size))
    return chunked_files

def find_unique_sids(chunked_files, pool):
    print("Find unique SIDs")
    sid_sets = pool.map(process_sids, chunked_files)
    sids = set()
    for chunk in sid_sets:
        for sid in chunk:
            sids.add(sid)
    return sids

def identify_domains(sid_users):
    print("Identify Domains")
    unique_domains = set()
    for user in sid_users:
        if len(user) > 3:
            unique_domains.add(user[3])
    return unique_domains

def separate_unresolved(sid_users):
    print("Separate unresolved SIDs")
    no_user = []
    identified_accounts = []
    for item in sid_users:
        if item[2]:
            identified_accounts.append(item)
        else:
            no_user.append(item)
    return identified_accounts, no_user

def second_pass_resolve(unresolved_sids, domain_groups):
    print('Checking unresolved SIDs against LDAP groups')
    still_unresolved = []
    resolved_sids = []
    for item in unresolved_sids:
        unresolved = True
        for domain in domain_groups:
            if item[0] in domain_groups[domain].keys():
                sid_line = [item[0], item[1], domain_groups[domain][item[0]], domain, 2]
                resolved_sids.append(sid_line)
                unresolved = True
                break
        if unresolved:
            still_unresolved.append(item)
    return resolved_sids, still_unresolved

def separate_users_groups(identified_accounts):
    print('Separate users and groups')
    identified_users = []
    identified_groups = []
    for item in identified_accounts:
        if item[4] == 1:
            identified_users.append(item)
        else:
            identified_groups.append(item)
    return identified_users, identified_groups

def make_sid_pairs(matched_users, matched_groups):
    paired_sids = {}
    paired_sids.update({user[0]:user[8] for user in matched_users})
    paired_sids.update({group[0]:group[6] for group in matched_groups})
    return paired_sids
    
def match_chunk_perms(passed):
    chunk, sid_pairs = passed
    new_perms=[]
    for file in chunk:
        new_file_perms = []
        current_sids = set()
        for item in file[2]:
            sid = item.split(';;;')[1][:-1]
            if sid.startswith('S-1-5-21-'):
                current_sids.add(sid)
        for item in file[2]:
            new_file_perms.append(item)
            perm_string = item.split(';;;')
            old_sid = perm_string[1][:-1]
            if old_sid.startswith('S-1-5-21-'):
                if old_sid in sid_pairs: 
                    if sid_pairs[old_sid] not in current_sids:
                        new_file_perms.append(f'{perm_string[0]};;;{sid_pairs[old_sid]})')
        new_perms.append(f'{file[0]}\n{file[1]}{''.join(new_file_perms)}{file[3]}\n')
    return new_perms

def match_perms(chunked_files, sid_pairs, pool):
    print('Creating new permission file.')
    new_file_perms = pool.map(match_chunk_perms, [(chunk, sid_pairs) for chunk in chunked_files])
    return new_file_perms