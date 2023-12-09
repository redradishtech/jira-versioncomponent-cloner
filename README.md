# Jira Project Versions/Components Cloner

This utility will clone Jira versions and components from one project to another, using Jira's REST APIs.

It was written to support the use-case where issues will be bulk-moved from one project to another, and project 
versions/components in the destination project must match those in the source project.

Currently it is only tested on self-hosted Jiras..

## Usage

Standard Python setup:
```
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```
Configuration is done in code. Edit `JiraVersionComponentCloner.py` and customize the `MyConfig` class:

```python
# Customize this class with your Jira connection details, and which projects you want to clone to/from.
class MyConfig(Config):
    access_method = "token"
    token = "<REDACTED>"
    # Alternatively:
    # access_method = "basic"
    # user = "jdoe"
    # password = "hunter2"
    baseurl = "http://redradish-jira.localhost:8080"
    srcproj = "TEMPLATE"
    destproj = "NEWCLIENT"
    # Which versions to copy
    versions: list[str] = Config.ALL
    # alternatively:
    # versions: list[str] = json.load(open("versions.json"))
    # Which components to copy
    components: list[str] = Config.ALL
    # Whether to make cloned versions unarchived, so issues can be moved to them
    unarchive = True
```

Now run:
```sh
(venv) jturner@jturner-desktop:~/redradishtech/jira-versioncomponent-cloner $ ./JiraVersionComponentCloner.py 
DEBUG:__main__:Connecting to Jira: http://redradish-jira.localhost:8080
DEBUG:__main__:Logged in as jturner
DEBUG:__main__:Copying all 2 of TEMPLATE's components from TEMPLATE to NEWCLIENT
Created from http://redradish-jira.localhost:8080/rest/api/2/component/10912 -> http://redradish-jira.localhost:8080/rest/api/2/component/10918
Created from http://redradish-jira.localhost:8080/rest/api/2/component/10913 -> http://redradish-jira.localhost:8080/rest/api/2/component/10919
DEBUG:__main__:Copying all 7 of TEMPLATE's components from TEMPLATE to NEWCLIENT
Created from http://redradish-jira.localhost:8080/rest/api/2/version/11217 -> http://redradish-jira.localhost:8080/rest/api/2/version/11238
Created from http://redradish-jira.localhost:8080/rest/api/2/version/11218 -> http://redradish-jira.localhost:8080/rest/api/2/version/11239
Created from http://redradish-jira.localhost:8080/rest/api/2/version/11219 -> http://redradish-jira.localhost:8080/rest/api/2/version/11240
Created from http://redradish-jira.localhost:8080/rest/api/2/version/11220 -> http://redradish-jira.localhost:8080/rest/api/2/version/11241
Created from http://redradish-jira.localhost:8080/rest/api/2/version/11221 -> http://redradish-jira.localhost:8080/rest/api/2/version/11242
Created from http://redradish-jira.localhost:8080/rest/api/2/version/11222 -> http://redradish-jira.localhost:8080/rest/api/2/version/11243
Created from http://redradish-jira.localhost:8080/rest/api/2/version/11223 -> http://redradish-jira.localhost:8080/rest/api/2/version/11244
```

## Dealing with archived versions

The code supports a config flag:
```python
    # Whether to make cloned versions unarchived, so issues can be moved to them
    unarchive = True
```
In Jira, you will find you cannot bulk-move issues while preserving their version if the destination project's 
version is archived. By running with `unarchive=True`, your destination project will have all versions unarchived, 
allowing you to bulk-move issues to them. You can then re-run with `unarchive=False` to re-set the archive status to 
that of the source project's versions.


## Customizing the list of components/versions

If you only want to clone a subset of versions or components, customize these lines in `MyConfig`:

```python
    versions: list[str] = Config.ALL
    components: list[str] = Config.ALL
```

E.g. to only copy a named list of versions:
```python
versions: list[str] = json.load(open("versions.json"))
```
where `versions.json` might contain:
```json
["1.0", "2.0", "3.0"]
```
You might like to generate this JSON with a database query.
For instance, say we plan to bulk-move issues with component `MYCOMPONENT` from project `TEMPLATE` into a new 
project. We only want to copy versions relevant to our `MYCOMPONENT` subset of issues, which can be identified with:

```sql
SELECT json_agg(distinct(v.vname)::varchar)
FROM project
JOIN jiraissue ON project.id=jiraissue.project
JOIN
  (SELECT *
   FROM nodeassociation
   WHERE association_type='IssueComponent') cna ON jiraissue.id= cna.source_node_id
JOIN
  (SELECT *
   FROM component
   WHERE cname='MYCOMPONENT') component ON component.id=cna.sink_node_id
JOIN
  (SELECT *
   FROM nodeassociation
   WHERE association_type='IssueFixVersion'
     OR association_type='IssueVersion') na ON na.source_node_id = jiraissue.id
JOIN projectversion v ON v.id=na.sink_node_id
WHERE project.pkey='TEMPLATE';
```