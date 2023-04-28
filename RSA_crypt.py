from math import gcd
import random
from sympy import randprime

# modulo inverzének kiszámítása
def mod_inverse(e, phi):
    d = 0
    new_d = 1
    r = phi
    while e != 0:
        q = r // e
        d, new_d = new_d, d - q * new_d
        r, e = e, r - q * e
    if d == 1:
        d = d + phi
    return d

# titkosításhoz szükséges kulcspárok generálása
def generate_key_pair():
    p = randprime(10**49, (10**50)-1)
    p_str= str(p)
    while len(p_str) != 50:
        p = randprime(10**49, (10**50)-1)
        p_str = str(p)
    p = int(p_str)

    q = randprime(10**49, 10**50-1)
    q_str= str(q)
    while len(q_str) != 50:
        q = randprime(10**49, 10**50-1)
        q_str = str(q)
    q = int(q_str)
    n = p*q

    phi = (p-1)*(q-1)
    e = random.randrange(2, phi)
    while gcd(e, phi) != 1:
        e = random.randrange(2, phi)
    d = mod_inverse(e, phi)
    return (e, n), (d, n)

public_key, private_key = generate_key_pair()
e, n = public_key
crypted_ip_list = []
ip_addr = "192.168.0.1"
for x in ip_addr:
    unicode_x = ord(x)
    pow_x = pow(unicode_x, e, n)
    crypted_ip_list.append(pow_x)
print(crypted_ip_list)

crypted_ip_hex = ""
for y in crypted_ip_list:
    crypted_ip_hex += "{:02x}".format(y)
print(crypted_ip_hex)

# visszafejtés
decrypted_ip = []
d, n = private_key
for x in crypted_ip_list:
    x = int(x)
    pow_x = pow(x, d, n)
    decrypted_chr = chr(pow_x)
    decrypted_ip += decrypted_chr
decrypted_ip = ''.join(decrypted_ip)
print(decrypted_ip)
