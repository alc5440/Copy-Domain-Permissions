"""
Module: correlate.py
Description: Correlates objects between domains

Author: Andrew Collings
Created: 2025-02-09
Updated: 2025-02-11
License: MIT
"""

import questionary
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, FuzzyCompleter
import sys

def users(filtered_users, domain_users, template_domain, target_domain):
    print('Correlating users')
    for i in range(len(filtered_users)):
        for j in domain_users[template_domain]:
            if j['name'] == filtered_users[i][2]:
                filtered_users[i].append(j['full_name'])
                break
    
    all_users = {user['full_name']:user['name'] for user in domain_users[target_domain]}
    no_user_match = []
    for i in range(len(filtered_users)):
        exact_matches = []
        for j in domain_users[target_domain]:
            if filtered_users[i][5] in j['full_name']:
                exact_matches.append([j['full_name'],j['name']])
        if len(exact_matches) == 1:
            filtered_users[i].extend(exact_matches[0])
        if len(exact_matches) > 1:
            selected_match = questionary.select(f'Multiple exact matches found for {filtered_users[i][5]} ({filtered_users[i][2]}), please select the correct one:', choices=[choice[0] for choice in exact_matches]).ask()
            filtered_users[i].extend([item for choice in exact_matches if choice[0] == selected_match for item in choice])
            
        if not exact_matches:
            potential_matches = {}
            for j in domain_users[target_domain]:
                if j['full_name']:
                    if j['full_name'].split()[0] == filtered_users[i][5].split()[0]:
                        potential_matches.update({j['full_name']:j['name']})
            if potential_matches:
                selected_match = questionary.select(f'No exact match was found for {filtered_users[i][5]} ({filtered_users[i][2]}), please select from the following rough matches:', choices=list(potential_matches.keys()) + ['None of these']).ask()
                if selected_match == 'None of these':
                    no_user_match.append(filtered_users[i])
                else:
                    filtered_users[i].extend([selected_match, potential_matches[selected_match]])
            else:
                manual_select = questionary.confirm(f"No match found for user {filtered_users[i][5]}. Would you like to select manually?").ask()
                if manual_select:
                    user_completer = FuzzyCompleter(WordCompleter(list(all_users.keys())+["None"], ignore_case=True))
                    print('Please enter the full name of a user or type "None" to cancel.')
                    print('You can use the arrow keys or Tab to auto complete. Please use auto completion to avoid unexpected behavior')
                    manual_match = prompt("Select a user then press Enter: ", completer=user_completer)
                    if manual_match == 'None':
                        no_user_match.append(filtered_users[i])
                    else:
                        filtered_users[i].extend([manual_match, all_users[manual_match]])
                else:
                    no_user_match.append(filtered_users[i])

    if no_user_match:
        print('The following users will not have permissions created in the target domain because no match was found:\n')
        for i in range(len(no_user_match)):
            print(f'{no_user_match[i][5]}', end='   ')
            if (i + 1) % 5 == 0:
                print()
        print()
        user_proceed = questionary.confirm('Do you want to continue?').ask()
        if not user_proceed:
            sys.exit()
        else:
            return [user for user in filtered_users if user not in no_user_match]
    else:
        return filtered_users

def groups(filtered_groups, domain_groups, target_domain):
    for j in domain_groups.keys():
        domain_groups[j] = {value: key for key, value in domain_groups[j].items()}
    group_modifier = input('If the groups in the target domain have a common suffix please enter it (including any spaces). Otherwise, just press Enter: ')
    no_group_match = []
    for i in range(len(filtered_groups)):
        exact_match = False
        no_match = True
        for j in domain_groups[target_domain].keys():
            if filtered_groups[i][2] + group_modifier == j or filtered_groups[i][2] == j:
                filtered_groups[i].extend([j, domain_groups[target_domain][j]])
                exact_match = True
                no_match = False
                break
            
        if not exact_match:
            potential_matches = []
            for j in domain_groups[target_domain].keys():
                if filtered_groups[i][2] in j:
                    potential_matches.append([j, domain_groups[target_domain][j]])
            if not potential_matches:
                for j in domain_groups[target_domain].keys():
                    if any(item in filtered_groups[i][2].split() for item in j.split()):
                        potential_matches.append([j,domain_groups[target_domain][j]])
                        

            if potential_matches:
                if not exact_match:
                    potential_matches = questionary.select(f'Please select from the potential matches for {filtered_groups[i][2]}: ', choices=[item[0] for item in potential_matches] + ['None of these']).ask()
                if potential_matches == 'None of these':
                    no_group_match.append(filtered_groups[i])
                else:
                    no_match = False
                    if not exact_match:
                        potential_matches = [potential_matches, domain_groups[target_domain][potential_matches]]
                    filtered_groups[i].extend(potential_matches)
            if no_match:
                select_manually = questionary.confirm(f'No rough matches found for {filtered_groups[i][2]}. Would you like to select manually?').ask()
                if select_manually:
                    group_completer = FuzzyCompleter(WordCompleter(list(domain_groups[target_domain].keys())+["None"], ignore_case=True))
                    print('Please enter the name of a group or type "None" to cancel.')
                    print('You can use the arrow keys or Tab to auto complete. Please use auto completion to avoid unexpected behavior')
                    manual_selection = prompt("Select a group then press Enter: ", completer=group_completer)
                    if manual_selection != 'None':
                        filtered_groups[i].extend([manual_selection, domain_groups[target_domain][manual_selection]])
                        no_match = False
            if no_match:
                no_group_match.append(filtered_groups[i])


    if no_group_match:
        print('The following groups will not have permissions created in the target domain because no match was found:\n')
        for i in range(len(no_group_match)):
            print(f'{no_group_match[i][2]}', end='   ')
            if (i + 1) % 5 == 0:
                print()
        print()
        group_proceed = questionary.confirm('Do you want to continue?').ask()
        if not group_proceed:
            sys.exit()
        else:
            return [group for group in filtered_groups if group not in no_group_match]
    else:
        return filtered_groups