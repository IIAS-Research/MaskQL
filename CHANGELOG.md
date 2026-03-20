# CHANGELOG

<!-- version list -->


## v1.1.0 (2026-03-20)

### Bug Fixes

- Align prod compose target and Trino Dockerfile naming
  ([`ea7e6ef`](https://github.com/IIAS-Research/MaskQL/commit/ea7e6ef90d894af48595d6b7be4fa29567e5bae9))

- Align Trino plugin build with Java 24
  ([`ab1cc86`](https://github.com/IIAS-Research/MaskQL/commit/ab1cc86c98ac2f20595dd70aceed82964d37c645))

- Allow table if one columns is directly allowed
  ([`7ef7276`](https://github.com/IIAS-Research/MaskQL/commit/7ef7276f94f03b1b128522f6e08daef23e408522))

- Auto cast
  ([`14c31a5`](https://github.com/IIAS-Research/MaskQL/commit/14c31a5648a9ade5b2b430112d0ce5a6747610e8))

- Scan sql server schema + ability to add schema item
  ([`41eb9a2`](https://github.com/IIAS-Research/MaskQL/commit/41eb9a2200add77df1be8e15da334d798bcdf6de))

- Tests
  ([`970c6a9`](https://github.com/IIAS-Research/MaskQL/commit/970c6a95cf2168e5f199ab89f72f63fb178fdbda))

### Features

- Connexion status
  ([`6fa399b`](https://github.com/IIAS-Research/MaskQL/commit/6fa399becbae1039f022cfe64a48d68a512a4ad5))

- Rework of config UI
  ([`0f6be97`](https://github.com/IIAS-Research/MaskQL/commit/0f6be97926904f57e2b930bc99c6578d8b0a1273))

- Sync schema, with refa of catalog objects
  ([`9d34e3b`](https://github.com/IIAS-Research/MaskQL/commit/9d34e3b869138bbcbebf7dbae43235ba48b92aa2))

- Versionning
  ([`ca83a81`](https://github.com/IIAS-Research/MaskQL/commit/ca83a81bacd57bdded6b57905dcf4de5764b3b8a))

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
