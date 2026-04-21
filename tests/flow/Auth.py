from pycognito import Cognito
import boto3

identity = boto3.client("cognito-identity")

class Auth:
    def __init__(self, user_pool, client_id, identity_pool):
        self.user_pool = user_pool
        self.client_id = client_id
        self.identity_pool = identity_pool

    def authenticate(self, username, password):
        u = Cognito(self.user_pool, self.client_id, username=username)
        u.authenticate(password=password)
        u.verify_tokens()
        self.id_token = u.id_token
        #print(u.id_token)
        #print("Username:" + u.username)

        identityId = identity.get_id(
                IdentityPoolId=self.identity_pool,
                Logins={
                    f"cognito-idp.us-east-1.amazonaws.com/{self.user_pool}": u.id_token
                }
        )['IdentityId']

        print(identityId)

        aws_cred = identity.get_credentials_for_identity(
                IdentityId=identityId,
                Logins={
                    f"cognito-idp.us-east-1.amazonaws.com/{self.user_pool}": u.id_token
                }
        )['Credentials']

        #print(aws_cred)

        idp = boto3.client('cognito-idp')

        self.access_token = u.access_token
        user_info = idp.get_user(AccessToken=u.access_token)
        sub = user_info["Username"]
        self.sub = sub

    def get_sub(self):
        return self.sub
    
    def get_access_token(self):
        return self.access_token