## 0.3.0 (2025-11-16)

### BREAKING CHANGE

- sentinel objects are working now

### Feat

- update pydantic handling for compatibility with Python 3.14 and above; improve type casting in various modules
- **sentinel.py**: added basic sentinel objects logic

### Fix

- **caster**: prevent joining and applying rules on safe-casted Caster instances
- add Sentinels section to navigation in mkdocs.yml
- **sentinels**: enhance Sentinel class with type parameter and initialization logic
- add missing remote configuration to mkdocs.yml
- **sentinels.py**: fixed type casting for enum-like sentinels
- **sentinels**: renamed module name
- add configuration context management with get_config, set_config, and get_env functions
- enhance type casting utilities and add new tests for assert_notnone and cast_notnone
- add is_instanceexact function and corresponding tests
- implement registry to support non-enumable code
- implement missing monad, pathx, and string utilities; update tests for new casting and path validation logic
- **data**: no longer considers a private field with ref as empty

### Refactor

- streamline code formatting and enhance task scheduler setup

## 0.2.8 (2025-06-15)

### Fix

- now properly supports sequence types on load and dump

## 0.2.17 (2025-08-18)

### Fix

- **caster**: prevent joining and applying rules on safe-casted Caster instances
- add Sentinels section to navigation in mkdocs.yml

## 0.2.16 (2025-08-17)

### BREAKING CHANGE

- sentinel objects are working now

### Feat

- **sentinel.py**: added basic sentinel objects logic

### Fix

- **sentinels**: enhance Sentinel class with type parameter and initialization logic
- add missing remote configuration to mkdocs.yml
- **sentinels.py**: fixed type casting for enum-like sentinels
- **sentinels**: renamed module name

## 0.2.15 (2025-08-11)

### Refactor

- streamline code formatting and enhance task scheduler setup

## 0.2.14 (2025-08-10)

### Fix

- add configuration context management with get_config, set_config, and get_env functions

## 0.2.13 (2025-08-08)

### Fix

- enhance type casting utilities and add new tests for assert_notnone and cast_notnone

## 0.2.12 (2025-08-08)

### Fix

- add is_instanceexact function and corresponding tests

## 0.2.11 (2025-08-03)

### Fix

- implement registry to support non-enumable code

## 0.2.10 (2025-07-16)

### Fix

- implement missing monad, pathx, and string utilities; update tests for new casting and path validation logic

## 0.2.9 (2025-07-16)

### Fix

- implement missing monad, pathx, and string utilities; update tests for new casting and path validation logic
- **data**: no longer considers a private field with ref as empty

## 0.2.8 (2025-06-15)

### Fix

- now properly supports sequence types on load and dump

## 0.2.7 (2025-06-15)

### Fix

- remove print statements

## 0.2.6 (2025-06-15)

### Fix

- **data**: add support for a ref parameter

## 0.2.5 (2025-06-14)

### Fix

- **data**: now properly supports aliases and defaults on converter functions

## 0.2.4 (2025-06-12)

### Fix

- **tests/misc-functions**: add function walk_object and change build framework to use uv

## 0.2.3 (2025-05-06)

### Fix

- removed print

## 0.2.2 (2025-05-02)

### Fix

- add retry functions and typex module

## 0.2.1 (2025-04-12)

## 0.2.0 (2025-04-12)

### Feat

- added jsonx and config

### Fix

- update cz config
- added tests for autodiscovery
- added support for autodiscovery
- removed gyver, env-star and lazyfields references
- added support for context-handler
