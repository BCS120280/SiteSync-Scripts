# Code Review: script-python Directory

**Date:** 2026-02-22
**Scope:** All 52 Python scripts under `script-python/`
**Platform:** Ignition (Inductive Automation) with Jython runtime

---

## Executive Summary

The `script-python/` directory contains Ignition Perspective scripting modules for the SiteSync IoT/IIoT platform. These scripts manage LoRaWAN devices, MQTT connections, PI System integration, tag operations, and dashboard rendering. The codebase has several **critical bugs**, **security concerns**, **dead code**, and **maintainability issues** that should be addressed.

---

## 1. CRITICAL BUGS

### 1.1 `dashboard/routing/code.py` - Wrong variable name (will crash at runtime)

**File:** `script-python/dashboard/routing/code.py:2`

The function parameter is `sensorType` but the body references `value`, which is undefined:

```python
def getTile(sensorType):
    if value in ("TEMPERATURE", "PRESSURE", "420ma", "FLOWMETER"):  # BUG: 'value' is not defined
```

**Fix:** Replace all references to `value` with `sensorType`.

---

### 1.2 `utils/QRCodeParser/code.py:97` - `parseVega` is incorrectly indented inside `getQRType`

The `parseVega` function is defined inside `getQRType` due to indentation, making it invisible at module scope. The `parse()` function at line 10 calls `parseVega(data)` at module scope, which will raise a `NameError`:

```python
def getQRType(data):
    ...
    else:
        return "DEVEUI"

	def parseVega(data):    # <-- indented inside getQRType, unreachable from parse()
```

**Fix:** Dedent `parseVega` to module level (zero indentation).

---

### 1.3 `PIIntegration/adapter/code.py:21` - Python 2 print statement

```python
print path  # Python 2 syntax, will fail in Python 3
```

This also appears in:
- `getSensors/code.py:47,74,75,81,82,98,134,135,226,259,260,369,441,442,483,552,553`
- `device/excelParser/code.py:34`

**Risk:** If the Ignition gateway ever upgrades to a Jython 3 runtime, all `print` statements (without parentheses) will become syntax errors.

---

### 1.4 `PIIntegration/status/code.py` - Duplicate function definitions

Lines 1-10 and 23-28 define `getTransmitterStatus()` and `isUsingTransmission()` twice. The first set uses tab indentation; the second uses spaces. The second definitions silently override the first:

```python
def getTransmitterStatus():       # lines 2-3 (tabs)
    return {}

def getTransmitterStatus():       # lines 23-25 (spaces) - overrides the first
    return {}
```

**Fix:** Remove the duplicate definitions (lines 23-28).

---

### 1.5 `getSensors/code.py:384` - `engUnits` referenced before assignment

In `rowFormatter()` at line 384-385:
```python
if tagTitle in trackedColumns and viewType != "Simple":
    items[tagName + "High"] = engUnits[0].value  # engUnits never defined
    items[tagName + "Low"] = engUnits[1].value
```

The code that would define `engUnits` (calling `system.tag.readBlocking`) is commented out on lines 382-383. This will throw a `NameError` at runtime whenever `viewType != "Simple"`.

---

### 1.6 `getSensors/code.py:294` - `deviceTagPaths` referenced before assignment

In `getTrackedColumns()`:
```python
def getTrackedColumns(deviceType, viewType):
    ...
    else:
        firstInstance = deviceTagPaths.values()[0]  # deviceTagPaths is not a parameter
```

`deviceTagPaths` is not passed as an argument and does not exist in the local scope.

---

### 1.7 `sparkplugSiteSync/code.py:6` - `sourcePath` referenced before assignment

In `triggerBirth()`:
```python
def triggerBirth(tagPath):       # parameter is 'tagPath'
    res = ""
    filterPath = cleanPathForFilter(sourcePath)   # BUG: 'sourcePath' undefined
```

**Fix:** Change `sourcePath` to `tagPath`.

---

### 1.8 `device/get/code.py:21` - Use of `unicode` type (Python 2 only)

```python
if type(m) == unicode:
```

`unicode` does not exist in Python 3. Use `isinstance()` and consider `str`/`bytes` for forward compatibility.

---

### 1.9 `addDevices/code.py:5` - Hardcoded internal URL

```python
PIAddress = "https://pgwgen002923.mgroupnet.com:5590/api/v1/configuration"
```

This is a hardcoded internal hostname with a port number. It will break in any non-development environment.

**Fix:** Move to a configuration source (tag, database, or PIIntegration settings).

---

### 1.10 `device/bulkUpload/code.py:79` - Boolean/integer comparison mismatch

```python
if charCheck(appKey, 32) > 0:   # charCheck returns True/False, not int
```

While `True > 0` evaluates to `True` in Python, this is misleading. Use `if charCheck(appKey, 32):` instead.

---

### 1.11 `PIIntegration/AF/code.py:51` - Backslash in format string

```python
endpoint = "{0}\{1}/{2}".format(repo, prefix, ss)
```

`\{` is not a recognized escape sequence and happens to work by accident in current Python versions, but this is fragile. Use a raw string `r"{0}\{1}/{2}"` or escape the backslash `"{0}\\{1}/{2}"`.

---

## 2. SECURITY CONCERNS

### 2.1 Credentials passed in plaintext via JSON

Multiple files serialize credentials (passwords, API tokens) as plain JSON strings without any encryption:

- `connections/mqtt/code.py:26` - `"password": pw.strip()`
- `connections/networkserver/code.py:17` - `"password": joinServerPW.strip()`
- `decoders/decoder/code.py:58` - `"apiPassword": password`

**Risk:** Credentials may appear in logs, tag values, or be visible in the Ignition Designer.

**Recommendation:** Use Ignition's built-in credential store or encrypt sensitive values before storage.

### 2.2 `decoders/downlinks/code.py:56-58` - Unsanitized format string injection

```python
def processAnyInputs(downlink, inputText):
    if "{0}" in downlink:
        return downlink.format(inputText)
```

If `inputText` comes from user input and `downlink` contains other format placeholders, this could cause `IndexError`/`KeyError` or unexpected string interpolation.

**Fix:** Use safer substitution, e.g., `downlink.replace("{0}", inputText)`.

### 2.3 `addDevices/code.py:1-3` - Global variable shadowing of Python builtins

```python
null = None
false = False
true = True
```

These shadow common Python concepts. While used to make JSON-like literals work, they create confusing global scope pollution and could mask real bugs.

### 2.4 No input validation on devEUI/appKey format

While length checks are performed, there is no hex character validation. Invalid characters in devEUI/appKey fields would pass length checks but fail silently downstream. For example, `device/createDevice/code.py:96` strips dashes but doesn't verify hex.

---

## 3. DEAD CODE AND UNREACHABLE CODE

### 3.1 `PIIntegration/adapter/code.py:52` - Unreachable `return False`

```python
def addToDataSelection(tagPathArray):
    ...
    if exists != None:
        return json.loads(exists)
    else:
        return {"status":False, "message":"Did not find PITag"}

    return False    # <-- Unreachable
```

### 3.2 `enterprise/tenant/code.py` - Entire module is effectively a constant

```python
def getDefaultApp():
    return 3
```

The rest is commented out. This hardcoded return value should be documented or replaced with actual configuration.

### 3.3 `setPointHelper/code.py` - All functions return `False`

All three functions (`applyToEngHigh`, `applyToEngLow`, `applyToTagValue`) are stubs that return `False`. This module appears unused/unfinished.

### 3.4 `dashboard/colors/code.py` and `utils/messages/actions/code.py` - Empty files

These modules are completely empty (0 bytes).

### 3.5 `device/bulkUpload/code.py:3` - Incorrect import

```python
from pip import utils   # This imports pip's utils, not the SiteSync utils module
```

This import is incorrect and likely dead (Ignition resolves `utils` differently at runtime).

---

## 4. CODE DUPLICATION

### 4.1 `pathValidator` - Duplicated in 2 files

Identical function in:
- `device/createDevice/code.py:45-59`
- `device/bulkuploadV2/code.py:60-73`

### 4.2 `charCheck` - Duplicated in 2 files

- `device/bulkUpload/code.py:64-68`
- `device/createDevice/code.py:61-65`

### 4.3 `formatMetaData` - Duplicated in 2 files

- `device/bulkUpload/code.py:6-14`
- `device/bulkuploadV2/code.py:134-142`

### 4.4 `formatName` - Duplicated in 2 files

- `device/bulkUpload/code.py:16-29`
- `device/bulkuploadV2/code.py:145-159`

### 4.5 `preventNullBasePath` - Duplicated in 2 files

- `device/createDevice/code.py:124-128`
- `device/tagOperations/code.py:33-37`

### 4.6 `saveTagPathForDevice` - Duplicated in 2 files

- `device/createDevice/code.py:130-145`
- `device/tagOperations/code.py:19-31`

### 4.7 `time_elapsed_since_date` logic - Duplicated 3 times

Nearly identical time-formatting logic in:
- `utils/timeFormatter/code.py:1-34` (`time_elapsed_since_date`)
- `utils/timeFormatter/code.py:37-69` (`timestampLastSeen`)
- `utils/timeFormatter/code.py:75-110` (`time_elapsed_since_dateTag`)

A fourth implementation exists in `getSensors/code.py:299-328` (`timeFormatter`).

### 4.8 `getColumnTemplate` / `getColumnTemplateHidden` - Duplicated with 1-field difference

`getSensors/code.py:565-657` and `getSensors/code.py:661-754` are nearly identical (~90 lines each), differing only in the `visible` field (`False` vs `True`). These should be a single function with a `visible` parameter.

### 4.9 `modelMapper` dict - Duplicated in 2 places

- `getSensors/code.py:136-144`
- `getSensors/code.py:414-421`

**Recommendation:** Extract all duplicated logic into shared utility functions.

---

## 5. INCONSISTENT ERROR HANDLING

### 5.1 Bare `except` clauses swallowing errors

Multiple files use bare `except:` or `except Exception as e:` that silently swallow errors:

- `device/excelParser/code.py:70-71` - `except: value = "error loading"`
- `device/excelParser/code.py:104-108` - `except Exception as e: dataset = None`
- `getSensors/code.py:244` - `except: items = None`
- `getSensors/code.py:361` - `except: tagValue = "None"`
- `getSensors/code.py:561` - `except: return ""`
- `decoders/decoder/code.py:70-71` - `except: api = None`

**Risk:** Silent failures make debugging extremely difficult. Errors are swallowed without logging.

### 5.2 Inconsistent result status formats

The codebase uses multiple incompatible status formats:
- `{"status": True/False, "message": "..."}` - PIIntegration modules
- `{"messageType": "SUCCESS"/"FAILURE", "message": "..."}` - resultParser
- `{"status": "ERROR", "message": "..."}` - device/get, updateDevice
- `{"status": "error", "message": "..."}` - addDevices, bulkUpload

`utils/resultParser/code.py` checks for both `messageType` and `status` keys but expects `status` to be the string `"SUCCESS"`, not a boolean. This means responses using `{"status": True}` will be evaluated as failures by `isResultSuccess()`.

---

## 6. CODE QUALITY AND MAINTAINABILITY

### 6.1 Mixed indentation (tabs vs spaces)

Most files use tabs, but several use spaces, and some mix both:
- `PIIntegration/status/code.py` - mixes tabs (lines 1-21) and spaces (lines 23-47)
- `utils/timeFormatter/code.py` - mixes tabs and spaces within the same function
- `device/bulkuploadV2/code.py` - uses spaces (unusual for this codebase)

This is a common source of `IndentationError` in Python.

### 6.2 Typos in identifiers

- `PIIntegration/AF/code.py:14` - `doesTagExtistInPI` (should be `doesTagExistInPI`)
- `createPITemplate/code.py:34` - `createReult` (should be `createResult`)
- `decoders/downlinks/code.py:26` - `getDonwlinkByID` (should be `getDownlinkByID`)
- `dynamicVisualtion/` - directory name misspelled (should be `dynamicVisualization`)
- `createPITemplate/code.py:4` - `"Creating PI isntance"` (should be `"instance"`)
- `utils/QRCodeParser/code.py:5` - `"LORAALIANCE"` (should be `"LORAALLIANCE"`)

### 6.3 No docstrings or type hints

Aside from `device/excelParser/code.py`, no functions have docstrings. No type hints are used anywhere. This makes understanding function contracts difficult.

### 6.4 Inconsistent naming conventions

- Module names: mix of camelCase (`bulkUpload`), lowercase (`decoder`), PascalCase (`QRCodeParser`, `PIIntegration`)
- Function names: mix of camelCase (`getMqttSettings`), snake_case (`bulk_upload`), PascalCase (`PIWebAPIPingStatus`)
- Variables: mix of camelCase (`devEUI`), snake_case (`tag_path`)

### 6.5 `getSensors/code.py` is 772 lines and does too much

This is the largest file and handles:
- Tag browsing and filtering
- Multiple table formatting strategies
- Column configuration generation
- Time formatting
- Metadata formatting
- Historical data queries
- Multiple device type mappings

**Recommendation:** Split into separate modules (table formatting, column config, device queries).

### 6.6 Magic numbers and hardcoded values

- `enterprise/tenant/code.py:3` - `return 3` (hardcoded app ID)
- `device/bulkUpload/code.py:87` - `0, 0` for lat/lon defaults
- `addDevices/code.py:5-6` - hardcoded PI server URL and component ID
- `sparkplugSiteSync/code.py:16` - `time.sleep(15)` with no explanation
- `getSensors/code.py:760` - `addDays(endTime, -14)` hardcoded 14-day window

### 6.7 `utils/sitehandler/code.py:32` - Import inside function

```python
def createSite():
    ...
    if tenant != None:
        import json   # json already imported at module level (line 1)
```

---

## 7. ARCHITECTURAL OBSERVATIONS

### 7.1 Tight coupling to Ignition runtime

All scripts depend on unresolvable runtime modules (`system`, `device`, `utils`, `decoders`, etc.) that exist only inside the Ignition gateway. The stub files (`device.py`, `system.py`, `utils.py`) only cover a fraction of the actual API surface used.

**Recommendation:** Expand stubs to cover all used APIs to enable IDE support and static analysis.

### 7.2 No unit tests

There are no test files anywhere in the repository. Given the complexity of the bulk upload, QR parsing, and PI integration logic, tests would catch many of the bugs identified above.

### 7.3 JSON serialization pattern is verbose and repetitive

Nearly every function follows this pattern:
```python
result = system.sitesync.someMethod(json.dumps(payload))
return json.loads(result)
```

A wrapper function could eliminate this boilerplate.

---

## 8. SUMMARY OF FINDINGS

| Severity | Count | Category |
|----------|-------|----------|
| Critical | 7 | Runtime crashes (NameError, undefined variables) |
| High | 4 | Security (plaintext creds, format injection, hardcoded URLs) |
| Medium | 9 | Dead code, unreachable code, empty modules |
| Medium | 9 | Code duplication |
| Low | 15+ | Style inconsistencies, typos, missing docs |

### Priority Fixes (Recommended Order)

1. **`dashboard/routing/code.py`** - Fix `value` -> `sensorType` (crash on every call)
2. **`utils/QRCodeParser/code.py`** - Dedent `parseVega` to module level (Vega QR codes broken)
3. **`sparkplugSiteSync/code.py`** - Fix `sourcePath` -> `tagPath` (Sparkplug births broken)
4. **`getSensors/code.py:384`** - Uncomment `engUnits` assignment or remove references (crash in non-Simple view)
5. **`getSensors/code.py:294`** - Pass `deviceTagPaths` as a parameter to `getTrackedColumns()`
6. **`PIIntegration/status/code.py`** - Remove duplicate function definitions
7. **`addDevices/code.py:5`** - Move hardcoded PI URL to configuration
8. **Standardize result status format** across all modules
9. **Extract duplicated functions** into shared utilities
10. **Add hex validation** for devEUI/appKey/joinEUI fields
