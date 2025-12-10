# ===== HELPER =====
import hashlib  
import ipaddress
import json
import numpy as np
import pandas as pd

##### FUNC ############
def ip_to_float(ip):
    try:
        ret = float(int(ipaddress.IPv4Address(ip)))
        
        if ret < 256:
            return ret/1e5
        
        return ret/1e9
    except:
        return 0.0  # for invalid or empty IPs
    
def sum_of_squares(partition):
    return pd.Series([(partition ** 2).sum()])

def string_to_float(s):
    if pd.notna(s):
        return int(hashlib.sha256(str(s).encode('utf-8')).hexdigest(), 16) % 10**8 / 1e8
    return 0


def down_ratio(f):
    return f/(f+1e-9)

# Bucket port
def bucket_port(port):
    if port < 1024:
        return 0  # Well-known
    elif port < 49152:
        return 1  # Registered
    else:
        return 2  # Dynamic/private
    
def astype(df):
    dtypes = {}    
    with open('features.json') as json_file:
        data = json.load(json_file)
        for key, type in data.items():
            if type == "int8":
                dtypes[key]= np.int8
            elif type == "float32":
                dtypes[key] = np.float32
        
        json_file.close()
    
    for key, type in data.items():
        if type == "int8":
            df[key] = df[key].astype(np.int8)
        elif type == "float32":
            df[key] = df[key].astype(np.float32)
        else:
            df[key] = df[key].astype(str)
            
    return df

def pre_astype(df):
    
    return df
##### FUNC ##############
