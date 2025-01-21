import bcrypt
from users.models import User

def create_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    print(f"hashed=>{type(hashed)}=>{hashed}")
    admin = User.create(username=username,
                        hash_password=hashed,
                        is_superuser=True,
                        is_active=True,)
    print('User created successfully', admin)
    return admin


if __name__ == '__main__':
    create_user('admin', "123456")