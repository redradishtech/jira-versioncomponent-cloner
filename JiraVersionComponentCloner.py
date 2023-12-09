#!/usr/bin/env python3
## Utility for cloning Jira project versions and components from one project to another. See README.md.
## Note: you MUST customize the MyConfig class below before running.

from jira import JIRA, Project
import logging

from config import Config

# Customize this class with your Jira connection details, and which projects you want to clone to/from.
class MyConfig(Config):
    access_method = "token"
    # token = os.environ["TOKEN"]
    token = "<REDACTED>"
    # Alternatively:
    # access_method = "basic"
    # user = "jdoe"
    # password = "hunter2"
    baseurl = "http://localhost:8080"
    srcproj = "SRCPROJ"
    destproj = "DESTPROJ"
    # Which versions to copy
    versions: list[str] = Config.ALL
    # alternatively:
    # versions: list[str] = json.load(open("versions.json"))
    # Which components to copy
    components: list[str] = Config.ALL
    # Whether to make cloned versions unarchived, so issues can be moved to them
    unarchive = True

class JiraVersionComponentCloner:

    def __init__(self, config: Config):
        self.config = config

    def clone(self):
        logger.debug(f"Connecting to Jira: {config.baseurl}")
        jira = config.getjira()
        logger.debug(f"Logged in as {jira.myself().get('key', '<unknown>')}")

        srcproj: Project = jira.project(config.srcproj)
        destproj: Project = jira.project(config.destproj)

        self.copy_fieldvals(jira, srcproj, destproj, "component", config.components, config)
        self.copy_fieldvals(jira, srcproj, destproj, "version", config.versions, config)

    def copy_fieldvals(self, jira: JIRA, srcproj: Project, destproj: Project, fieldname: str, fields_to_copy: list[str],
                       config: Config):
        """
    Copy versions or components (whatever `fieldname` says) from project `srcproj` to `destproj`.
        :param jira: Jira instance to connect to
        :param srcproj: Project the field values come from
        :param destproj: Project the field values be created in
        :param fieldname: Must be "version" or "component"
        :param fields_to_copy: Subset of components/versions to copy, as JSON list of name strings
        """

        def get_fields(proj: Project, fieldname: str):
            if fieldname == "component":
                return jira.project_components(proj.key)
            elif fieldname == "version":
                return jira.project_versions(proj.key)
            elif fieldname == "role":
                return jira.project_roles(proj.key)
            else:
                raise ValueError(f"Unhandled field type: {fieldname}")

        def differing_fields(srcfield, destfield, config: Config):
            # The assignee of a component will be inherited from the project if assigneeType=PROJECT_LEAD, so ignore
            ignorable = ['id', 'self', 'project', 'projectId', 'assignee', 'realAssignee']
            srcvals_trimmed = {k: v for k, v in srcfield.raw.items() if k not in ignorable}
            destvals_trimmed = {k: v for k, v in destfield.raw.items() if k not in ignorable}
            diff = []
            for field, srcval in srcvals_trimmed.items():
                if not field in destvals_trimmed:
                    logger.debug(f"{destproj.key} {fieldname} {destfield.name} is missing {field}")
                    diff.append(field)
                else:
                    destval = destvals_trimmed[field]
                    if destval != srcval:
                        logger.debug(
                            f"{destproj.key} {fieldname} {srcfield.name} {field} is {destval}, but we want {srcval}")
                        diff.append(field)

            # logger.debug(f"{srcval} and {destval} are functionally identical")
            return diff


        # FIXME: copy_fieldvals has if/then/else clauses for each fieldname type, which is ugly.
        #  In future, define a JiraField class with methods to get all field values, get one by name, etc
        if fields_to_copy is None:
            logger.debug(f"No {fieldname} to be copied, per configuration")
            return
        elif fields_to_copy == Config.ALL:
            src_fields = get_fields(srcproj, fieldname)
            logger.debug(
                f"Copying all {len(src_fields)} of {srcproj.key}'s components from {srcproj.key} to {destproj.key}")
        elif isinstance(fields_to_copy, list):
            src_fields = [c for c in get_fields(srcproj, fieldname) if str(c.name) in fields_to_copy]
            src_field_names = [c.name for c in src_fields]
            diff = set(fields_to_copy) - set(src_field_names)
            if len(diff) > 0:
                raise ValueError(f"The following {fieldname}s you specified are not in {srcproj} Jira: {diff}")
            logger.debug(f"Copying {len(src_fields)} {fieldname}s from {srcproj.key} to {destproj.key}")
        else:
            raise ValueError(f"{fieldname}s = {fields_to_copy} is an unhandled type")

        dest_fields = get_fields(destproj, fieldname)  # Get existing versions/components in destination proj

        for srcfield in src_fields:
            destfield = next((v for v in dest_fields if v.name == srcfield.name), None)
            if config.unarchive:
                # The 'unarchive' flag means we want the destination version unarchived, regardless of the src version's status
                # The simplest way to get this is to pretend that the source was unarchived, so the code later makes the destination unarchived too
                srcfield.raw["archived"] = False
            if destfield:
                diff = differing_fields(srcfield, destfield, config)
                if not diff:
                    logger.debug(f"{destproj.key} {fieldname} {destfield} already exists, identically to source")
                    continue
                else:
                    logger.debug(
                        f"{fieldname} {destfield} exists, and is different to what we want ({str(diff)}). We will update it")
            else:
                # Does not exist yet, so create
                if fieldname == "component":
                    destfield = jira.create_component(name=srcfield.name, project=destproj.key)
                elif fieldname == "version":
                    destfield = jira.create_version(name=srcfield.name, project=destproj.key)

            newfields = srcfield.raw.copy()
            del newfields['self']
            del newfields['id']
            if fieldname == "component":
                del newfields['project']
                del newfields['projectId']
            elif fieldname == "version":
                if {'releaseDate', 'userReleaseDate'} <= set(newfields):
                    del newfields['releaseDate']
                if {'startDate', 'userStartDate'} <= set(newfields):
                    del newfields['startDate']
            if fieldname == "version":
                if not destfield.archived and newfields["archived"]:
                    logger.debug(f"Archiving {destproj.key} {fieldname} {destfield}")
                    # Due to what must be a bug, setting 'archived' can't be done with the other params. It must
                    # be done on its own
                    destfield.update(archived=True)
            destfield.update(fields=newfields)
            print(f"Created from {srcfield.self} -> {destfield.self}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # Set to DEBUG if you want HTTP logs
    logger = logging.getLogger(__name__)

    config = MyConfig()
    cloner = JiraVersionComponentCloner(config)
    cloner.clone()
