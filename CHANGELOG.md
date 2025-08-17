# CHANGELOG

<!-- version list -->

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
