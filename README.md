# Xray pult
> Simple set of scripts for setting up and manipulating Xray server

#### Features
- Lightweight API for user management
- Easy to use unix way utils for manipulating API
- Built-in subscription page per user (you can provide subscription to apps like Happ: `http://your-server:port/sub/user`)

#### Setup

###### Server
0. Install `docker` and `docker-compose`
1. Create `config.json`
2. Create `sub.txt` from example
3. Create `.env` from example
4. Start container: `sudo docker compose up -d`

###### Client
0. Install `curl` and `jq`
1. Create `HOST` in `utils` from example
2. Use scripts to manipulate server:
```sh
cd utils

# Register new user
./add user1

# Delete user
./ban user1

# Get subscription per user data
./sub user1
```


