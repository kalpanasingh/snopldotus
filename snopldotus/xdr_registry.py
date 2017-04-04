import uuid

class Registry:
    '''A registry of one-time tokens for authenticating off-site requests'''
    def __init__(self):
        self.registry = {}

    def register(self, username, application):
        '''Create a new token for a username/application pair.

        Any existing token is overwritten.
        '''
        token = uuid.uuid4().hex
        self.registry[(username, application)] = token
        return token

    def validate(self, username, application, token):
        '''Check whether a token matches for a username/application pair.

        If the match is successful, it is removed from the registry.
        '''
        if (username, application,) in self.registry:
            if self.registry[(username, application)] == token:
                del self.registry[(username, application)]
                return True

        return False

registry = Registry()

