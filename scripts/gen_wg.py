import os
import subprocess
import random
import ipaddress
from jinja2 import Template

PEER_DIR = "peers"
TEMPLATE_PATH = "templates/wg.j2"
OUTPUT_DIR = "secrets/wireguard"
KEY_DIR = "secrets/keys"
MY_ASN = "4242420513"

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(KEY_DIR, exist_ok=True)

# Generate a new WireGuard keypair if not already generated
priv_key_path = os.path.join(KEY_DIR, "wg_private.key")
pub_key_path = os.path.join(KEY_DIR, "wg_public.key")

if not os.path.exists(priv_key_path):
    private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
    with open(priv_key_path, "w") as f:
        f.write(private_key)
    public_key = subprocess.check_output(["wg", "pubkey"], input=private_key.encode()).decode().strip()
    with open(pub_key_path, "w") as f:
        f.write(public_key)
else:
    with open(priv_key_path) as f:
        private_key = f.read().strip()
    with open(pub_key_path) as f:
        public_key = f.read().strip()

# Generate random local address in 192.0.0.0/8 or 169.254.0.0/16
local_ipv4_pool = [
    ipaddress.IPv4Network("192.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16")
]
selected_network = random.choice(local_ipv4_pool)
random_ip = str(random.choice(list(selected_network.hosts()))) + "/32"

# Generate random port in dynamic range
random_port = random.randint(49152, 65535)

local_config = {
    "private_key": private_key,
    "local_address": random_ip,
    "listen_port": random_port,
}

# Write our own public key to a file named after our ASN
pub_out_path = os.path.join(OUTPUT_DIR, f"{MY_ASN}.pub")
with open(pub_out_path, "w") as f:
    f.write(public_key + "\n")

# Load Jinja2 template
with open(TEMPLATE_PATH) as f:
    tmpl = Template(f.read())

# Process each peer file
for fname in os.listdir(PEER_DIR):
    if not fname.endswith(".conf"):
        continue

    peer = {}
    with open(os.path.join(PEER_DIR, fname)) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                peer[k.strip()] = v.strip()

    rendered = tmpl.render(**local_config, peer=peer)
    asn = peer.get("ASN", "unknown")
    out_path = os.path.join(OUTPUT_DIR, f"{asn}.conf")

    with open(out_path, "w") as out:
        out.write(rendered)
