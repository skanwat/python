#!/usr/bin/env python3

import os, getopt, sys
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
import re

#This script get the list of secrets from AKV starting with secret-list and replaces the token in one of the secrets and sets te secret again

target_env = os.environ.get('TARGET_ENV')
if target_env == 'dev':
  vault_url = 'https://dev.vault.azure.net'
elif target_env == 'test':
    vault_url =  'https://test.vault.azure.net/'
elif target_env == 'hard':
    vault_url = 'https://hard.vault.azure.net'
elif target_env == 'stage':
    vault_url = 'https://staging.vault.azure.net'
elif target_env == 'prod':
    vault_url = 'https://prod.vault.azure.net'    
    
arm_tenant_id = os.environ.get('ARM_TENANT_ID')
arm_client_id = os.environ.get('ARM_CLIENT_ID')
arm_client_secret = os.environ.get('ARM_CLIENT_SECRET')
token_to_update = os.environ.get('TOKEN_TO_UPDATE')
update_existing = False
tenant = os.environ.get('TENANT')


def has_number_at_end(string):
    # Regular expression pattern to match a number at the end of a string
    pattern = r"\d+$"
    
    # Check if the pattern matches the string
    match = re.search(pattern, string)
    
    # Return True if a match is found, False otherwise
    return match is not None

# Appending contents to a file
def append_to_file(file_path, content):
    with open(file_path, "a") as file:
        file.write(content)

# Reading contents from a file
def read_file(file_path):
    with open(file_path, "r") as file:
        content = file.read()
    return content

def get_number_from_string(string):
    # Extract the number from the end of the string
    number = ""
    for char in reversed(string):
        if char.isdigit():
            number = char + number
        else:
            break
    return int(number)

def find_string_with_highest_number(strings):
    # Sort the strings based on the number at the end
    sorted_strings = sorted(strings, key=get_number_from_string)

    # Return the string with the highest number at the end
    return sorted_strings[-1]   

def extract_number_from_string(string):
    # Regular expression pattern to match a number in the string
    pattern = r"\d+"
    
    # Find all occurrences of the pattern in the string
    matches = re.findall(pattern, string)
    
    # Return the first match (if any)
    if matches:
        return int(matches[0])
    else:
        return None     

key_vault_url = vault_url       
credentials = ClientSecretCredential(tenant_id=arm_tenant_id,client_id=arm_client_id,client_secret=arm_client_secret,connection_verify=False)

secret_client = SecretClient(vault_url=key_vault_url, credential=credentials)

# Get all secrets
secrets = secret_client.list_properties_of_secrets()

# Grep for a specific secret
target_secret_name = 'service-token'
secret_name_list=[]

#Search for all the secrets starting with service-token and form a list
for secret in secrets:
    name=secret.name
    if name.startswith(target_secret_name):
        #print(name)
        if has_number_at_end(name):
          secret_name_list.append(name)



       
#print list of camunda secrets in AKV
print("list of camunda secrets: {}",secret_name_list)

#secret has all the tenants with Auth in the end
tenant_start=tenant+'Auth'
    
#Loop through all the camunda secrets to find if the token already exists       
for camunda_list in secret_name_list:
    #get the secret and it value    
    camunda_secret = secret_client.get_secret(camunda_list)
    camunda_secret_value = camunda_secret.value
    print("old camunda token value before updation {}",camunda_secret_value)
    
    #Check if tenant exists in the current secret in loop, if exists replace it
    if tenant in camunda_secret_value:
        print("token exists in {}", camunda_list)
        update_existing = True
        # Split the secret value into lines
        lines = camunda_secret_value.split('\n')
        
        # Iterate through the lines and replace the value for tenantA
        for i, line in enumerate(lines):
            if line.startswith(tenant_start):
              lines[i] = f"{tenant_start}={token_to_update}"
        # Recreate the modified secret value with newlines
        new_secret_value = '\n'.join(lines)
       
        print("--------------------------------------------")
        print("Updated camunda token secret value: {}",new_secret_value)
        updated_secret = secret_client.set_secret(camunda_list, new_secret_value)
        break       


if update_existing == False:
    #find the secret with highest number in end
    result = find_string_with_highest_number(secret_name_list)
    secret_name_with_highest_no = result
    
    #Get the secret value
    secret_max_no = secret_client.get_secret(secret_name_with_highest_no)
    secret_max_no_value = secret_max_no.value
    print(secret_max_no_value)
    
    output_file_path = "/tmp/file.txt"
    value_length = len(secret_max_no_value)
    if value_length <= 25 * 1024:
        print("Secret value is within the limit.")
        append_to_file(output_file_path, secret_max_no_value)
        append_to_file(output_file_path, '\n')
        append_to_file(output_file_path, f"{tenant_start}={token_to_update}")
        file_contents = read_file(output_file_path)
        updated_secret = secret_client.set_secret(secret_name_with_highest_no, file_contents)
    else:
        print("Secret value exceeds the limit.")
        print("Create new Camunda Service Token Secret")
        secret_digit = secret_name_with_highest_no[-2]
        new_secret_digit = int(secret_digit) + 1
        two_digit_string = "{:02d}".format(new_secret_digit)
        new_secret_name = 'service-token-' + two_digit_string
        print("New Secret Name for Camunda token:" , new_secret_name)
        secret = secret_client.set_secret(new_secret_name, f"{tenant_start}={token_to_update}")



    # #Read the secret again to verify if all looks good
    # secret = secret_client.get_secret(secret_name)
    # secret_value = secret.value
    # print(secret_value)





