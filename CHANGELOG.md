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
  ([`11b8fa5`](https://gitlab.domchurs.ad/eds/maskql/-/commit/11b8fa5475059c52ebfa95dc2be2f75185de1970))


## v1.0.1 (2025-09-09)

### Bug Fixes

- Catalog From
  ([`1081af4`](https://gitlab.domchurs.ad/eds/maskql/-/commit/1081af406e81d47e6c3396d19dc63ccb24cb31bc))

- Must have public network to access database
  ([`6679c21`](https://gitlab.domchurs.ad/eds/maskql/-/commit/6679c21f7498cdb96f7579361fdf3200229eb3d0))


## v1.0.0 (2025-09-08)

### Features

- Here is the v1
  ([`0bee3cf`](https://gitlab.domchurs.ad/eds/maskql/-/commit/0bee3cf1a712ce18d7a1b22e43a12c05e0f8a5d6))


## v0.6.0 (2025-09-02)

### Bug Fixes

- Always allow system catalogs
  ([`8938691`](https://gitlab.domchurs.ad/eds/maskql/-/commit/8938691a4fe94105e0ff65c7c2ba77f17dbc7ef5))

- Ci
  ([`14378e6`](https://gitlab.domchurs.ad/eds/maskql/-/commit/14378e63a47a37014b628357ee36618ac4a671d4))

- Ci
  ([`80c98a1`](https://gitlab.domchurs.ad/eds/maskql/-/commit/80c98a12eeceae392f4056da16fde39cf8fbec54))

- Get submodules in cicd
  ([`56c843f`](https://gitlab.domchurs.ad/eds/maskql/-/commit/56c843faa4b6bcafc0919b5164465d22dea1d9a9))

- Pass HF_TOKEN with tox
  ([`9f14fe4`](https://gitlab.domchurs.ad/eds/maskql/-/commit/9f14fe47109dfc3cacad1a4ae5f94f933f6f0e25))

- Quicker Dockerfile, avoid crash when apply mask on empty string
  ([`b90e6f9`](https://gitlab.domchurs.ad/eds/maskql/-/commit/b90e6f94ad8a45d04f63d7dcdee0d8bee7a5d277))

- Tests
  ([`e357750`](https://gitlab.domchurs.ad/eds/maskql/-/commit/e357750c378327bb6234d5047b27f12db30e6710))

- Tests
  ([`dc94e1a`](https://gitlab.domchurs.ad/eds/maskql/-/commit/dc94e1a5c5c1503743759f9eb46eaf67d7ad4aad))

### Features

- Basic basis for the Mask plugin
  ([`7149941`](https://gitlab.domchurs.ad/eds/maskql/-/commit/7149941244f469ca017bf55bf725b589519309aa))

- Configuration with front interface
  ([`77074a5`](https://gitlab.domchurs.ad/eds/maskql/-/commit/77074a56f0ff8db090e945a967c4d7857fc105e2))

- Mask to encrypt with AES256
  ([`f982723`](https://gitlab.domchurs.ad/eds/maskql/-/commit/f982723af6388a45da6f11eebb0298f31785d9cb))

- Use IIAS pseudo package, extract text from pdf, fixes
  ([`79e9b80`](https://gitlab.domchurs.ad/eds/maskql/-/commit/79e9b8003093b923e9afdd3ce3bf57a87e34546c))

- We can now encrypt any type
  ([`f0cfd1a`](https://gitlab.domchurs.ad/eds/maskql/-/commit/f0cfd1ad072d53243568bb2f7cd15828de7c7cce))

### Testing

- Crypt and decrypt all types + fixes
  ([`f501af8`](https://gitlab.domchurs.ad/eds/maskql/-/commit/f501af85c236a8f08fa381acace06600f69b6385))


## v0.5.0 (2025-08-20)

### Bug Fixes

- Force trino to scan catalog. Dirty..
  ([`770be3c`](https://gitlab.domchurs.ad/eds/maskql/-/commit/770be3c16062fbf8363218527de9f2240854643d))

### Features

- Access control with API fully working
  ([`69c336f`](https://gitlab.domchurs.ad/eds/maskql/-/commit/69c336fe29391f4ab7aa06619f09231eaffbbff7))

- Add rules in seed
  ([`55b53eb`](https://gitlab.domchurs.ad/eds/maskql/-/commit/55b53ebc15ece7a72717d2a4a46dbae3da6200d1))

- Full ACL with API
  ([`27c4139`](https://gitlab.domchurs.ad/eds/maskql/-/commit/27c413981162540b1e1b90202dd9df0d01ece27d))

- Gateway user and admin user working with policies on routes
  ([`6055959`](https://gitlab.domchurs.ad/eds/maskql/-/commit/6055959345c7d1955d9a7bdf7bfb1a974200ce19))

- Models etc for users
  ([`b7fd18c`](https://gitlab.domchurs.ad/eds/maskql/-/commit/b7fd18c180876e66e15a6e74da5c67f2969e3823))

- Rules models, routes, schema, db and test
  ([`9a85da7`](https://gitlab.domchurs.ad/eds/maskql/-/commit/9a85da7d19e61a1d6403915c57e604f0e4c2c3b3))

### Testing

- Test User API and adapt old ones to new policies
  ([`7ff13e5`](https://gitlab.domchurs.ad/eds/maskql/-/commit/7ff13e58a971ba9bcac32724749a6c980ff100f2))


## v0.4.0 (2025-08-17)

### Features

- Catalog CRUD, catalog sync with Trino
  ([`8d2f747`](https://gitlab.domchurs.ad/eds/maskql/-/commit/8d2f7476d7db17375e0f7a47acd7905846ee3314))

- Init alembic for migrations
  ([`1f6dfe2`](https://gitlab.domchurs.ad/eds/maskql/-/commit/1f6dfe2ac37c18ad0f384488d3cfe593ce7dd6a9))

### Testing

- Adding seeds and Catalog API tests
  ([`179bd9c`](https://gitlab.domchurs.ad/eds/maskql/-/commit/179bd9cb62d0f117b648f53f4ab06a6747e32beb))


## v0.3.0 (2025-08-17)

### Features

- ACL Java Plugin now ask MaskQL API for user permissions and masks
  ([`065db12`](https://gitlab.domchurs.ad/eds/maskql/-/commit/065db12d52bae2a641b0b3ce611d7d0960de0b2c))

- ACL routes
  ([`4b0f63a`](https://gitlab.domchurs.ad/eds/maskql/-/commit/4b0f63a0a481cd3edfa106e13417f2f904657d24))

### Testing

- Arbitrary rule on client table
  ([`37e4876`](https://gitlab.domchurs.ad/eds/maskql/-/commit/37e4876dbbcf37d0836cb1f647f8b66babf25b58))


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
