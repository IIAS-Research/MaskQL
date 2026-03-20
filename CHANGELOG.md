# CHANGELOG

<!-- version list -->

> Historical entries predate the GitHub release migration. Private GitLab commit links were removed; future releases are generated from GitHub.

## v1.0.2 (2025-09-15)

### Bug Fixes

- Rules logic & typo
  (`11b8fa5`)


## v1.0.1 (2025-09-09)

### Bug Fixes

- Catalog From
  (`1081af4`)

- Must have public network to access database
  (`6679c21`)


## v1.0.0 (2025-09-08)

### Features

- Here is the v1
  (`0bee3cf`)


## v0.6.0 (2025-09-02)

### Bug Fixes

- Always allow system catalogs
  (`8938691`)

- Ci
  (`14378e6`)

- Ci
  (`80c98a1`)

- Get submodules in cicd
  (`56c843f`)

- Pass HF_TOKEN with tox
  (`9f14fe4`)

- Quicker Dockerfile, avoid crash when apply mask on empty string
  (`b90e6f9`)

- Tests
  (`e357750`)

- Tests
  (`dc94e1a`)

### Features

- Basic basis for the Mask plugin
  (`7149941`)

- Configuration with front interface
  (`77074a5`)

- Mask to encrypt with AES256
  (`f982723`)

- Use IIAS pseudo package, extract text from pdf, fixes
  (`79e9b80`)

- We can now encrypt any type
  (`f0cfd1a`)

### Testing

- Crypt and decrypt all types + fixes
  (`f501af8`)


## v0.5.0 (2025-08-20)

### Bug Fixes

- Force trino to scan catalog. Dirty..
  (`770be3c`)

### Features

- Access control with API fully working
  (`69c336f`)

- Add rules in seed
  (`55b53eb`)

- Full ACL with API
  (`27c4139`)

- Gateway user and admin user working with policies on routes
  (`6055959`)

- Models etc for users
  (`b7fd18c`)

- Rules models, routes, schema, db and test
  (`9a85da7`)

### Testing

- Test User API and adapt old ones to new policies
  (`7ff13e5`)


## v0.4.0 (2025-08-17)

### Features

- Catalog CRUD, catalog sync with Trino
  (`8d2f747`)

- Init alembic for migrations
  (`1f6dfe2`)

### Testing

- Adding seeds and Catalog API tests
  (`179bd9c`)


## v0.3.0 (2025-08-17)

### Features

- ACL Java Plugin now ask MaskQL API for user permissions and masks
  (`065db12`)

- ACL routes
  (`4b0f63a`)

### Testing

- Arbitrary rule on client table
  (`37e4876`)


## v0.2.0 (2025-08-16)

Trino is now on a private network and so can no longer be reach outside of MaskQL's containers. MaskQL's FastAPI backend handle auth and https before passing request to Trino.


## v0.1.0 (2025-08-15)

- Initial Release
- First bricks of the project :
  - Trino with configuration file
  - Postgresql for testing
  - Unit test with tox
  - Makefile
  - uv env
