# CHANGELOG

<!-- version list -->

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
