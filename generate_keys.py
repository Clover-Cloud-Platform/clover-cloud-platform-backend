import rsa

(pubkey, privkey) = rsa.newkeys(2048)

with open('public.pem', 'w+') as f:
    f.write(pubkey.save_pkcs1().decode('utf-8'))

with open('private.pem', 'w+') as f:
    f.write(privkey.save_pkcs1().decode('utf-8'))
