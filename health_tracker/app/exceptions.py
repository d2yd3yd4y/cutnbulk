class AuthRedirect(Exception):
    def __init__(self, url: str):
        self.url = url
        super().__init__(url)
