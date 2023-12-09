import re
from jira import JIRA


class Config:
    """
    Base Config class -- subclass this to configure the Cloner as to how to access your Jira (`baseurl`, `access_method` etc)
    and what project's versions/components to copy (`srcproj`, `destproj`).
    If you need something other than username/password ('basic') or Personal Access Token ('token') auth, then
    your subclass can also override `getjira()`.
    """
    ALL = "all"
    required = ['baseurl', 'access_method', 'srcproj', 'destproj']
    baseurl: str = None
    access_method: str = "basic"  # or 'token', 'oauth', 'jwt', 'kerberos'
    jira: JIRA = None
    user: str = None
    password: str = None
    token: str = None
    srcproj: str = None
    destproj: str = None
    components: list[str] = None
    versions: list[str] = None
    unarchive: bool = False

    def __init_subclass__(cls, **kwargs):
        """
        Called when (as expected) this class is subclassed with real data, this constructor validates the configuration.
        """
        if not hasattr(cls, "access_method"):
            raise ValueError(f"access_method configuration field must be defined")
        if cls.access_method == "basic":
            cls.required.extend(['user', 'password'])
        elif cls.access_method == "token":
            cls.required.append("token")
        for req in cls.required:
            if req not in cls.__dict__:
                raise ValueError(f"{req}' is missing in {cls.__name__} configuration")
        if not hasattr(cls, "components") and not hasattr(cls, "versions"):
            raise ValueError("Must include either 'versions' or 'components'")
        for field in ["components", "versions"]:
            if hasattr(cls, field):
                val = cls.__dict__[field]
                if not (val == "all" or val == None):
                    if not all(isinstance(x, str) for x in val):
                        raise ValueError(f"{cls.__name__}.{field} must be \"all\", None or an array of str")
        if not re.match(r"https?://.+", cls.baseurl):
            raise ValueError(f"baseurl '{cls.baseurl}' does not look like a valid URL")

        for field in ["srcproj", "destproj"]:
            val = cls.__dict__[field]
            if not re.match(r"^[A-Z]+$", val):
                raise ValueError(f"{field} is expected to be [A-Z]+ project key, not '{val}'")

    def getjira(self):
        if not self.jira:
            if self.access_method == "basic":
                self.jira = JIRA(server=self.baseurl, basic_auth=(self.user, self.password))
            elif self.access_method == "token":
                self.jira = JIRA(server=self.baseurl, token_auth=self.token)
            else:
                raise ValueError(f"access_method '{self.access_method}' unimplemented.")

        return self.jira
