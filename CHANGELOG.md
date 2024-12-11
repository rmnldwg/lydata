# Changelog

All notable changes to this project will be documented in this file.

## [0.2.3] - 2024-12-05

### 🚀 Features

- Add `central` to shortname columns

### 🐛 Bug Fixes

- `&` and `|` with `None` return original `Q`. Previously, `Q(...) | None` would return a query that evaluated to `True` everywhere.

### 📚 Documentation

- List defined operators on `Q` (`&`, `|`, `~`, `==`) in the docstring of `CombineQMixin`.

### 🧪 Testing

- ensure that `&` and `|` with `None` return original `Q`.

## [0.2.2] - 2024-12-03

### 🚀 Features

- *(utils)* Add better update func for pandas

### 🐛 Bug Fixes

- Order of sub-/superlevel inference
- Don't ignore present sub-/superlvl cols

## [0.2.1] - 2024-11-29

### 🐛 Bug Fixes

- If an LNL of a patient was unobserved (i.e., all diagnoses `None`), then the method `ly.combine()` returns `None` for that patient's LNL. Fixes [#13]

### 🧪 Testing

- Change the doctest of `ly.combine()` to check whether [#13] was fixed.

## [0.2.0] - 2024-11-14

### 🚀 Features

- Can now combine `Q` with `None` to yield `Q` again.
- Add `contains` operator to `C`, `Q` objects. This calls pandas' `str.contains` method.

### 🧪 Testing

- Fix wrong name in doctests

### Change

- [**breaking**] Add, rename, delete several methods:
  - `LyDatasetConfig` is now just `LyDataset`
  - the `path` property is now `path_on_disk`
  - the `get_url()` method has been removed
  - the `get_description()` method has been removed
  - added `get_content_file()` method to fetch and store remove content
  - `load()` was renamed to `get_dataframe()`
  - the `repo` argument was changed to `repo_name`
- *(utils)* [**breaking**] Rename `enhance` func to `infer_and_combine_levels`.

### Remove

- [**breaking**] Two unused funcs for markdown processing were removed
- *(load)* [**breaking**] Drop `join_datasets`, since it's not needed. All it did was run `pd.concat(...)`.

## [0.1.2] - 2024-10-31

### 🐛 Bug Fixes

- *(load)* Fix a bug where datasets with multiple subsites (e.g. `2024-umcg-hypopharynx-larynx`) would cause an error because of a missing `maxsplit=2` argument.

## [0.1.1] - 2024-10-31

### 🚀 Features

- *(load)* add `get_repo()` method that fetches remote repository information for a `LyDatasetConfig
- *(load)* make authentication more flexible
- *(utils)* put sub-/superlevel inference in its own utility function

## [0.1.0] - 2024-10-28

### 🚀 Features

- *(utils)* Add often needed `enhance` function to complete sub-/superlevel involvement and infer maximum likelihood status.

### 🐛 Bug Fixes

- Avoid `KeyError` in `infer_superlevels`

### ⚙️ Miscellaneous Tasks

- Add link to release 0.0.4

### Change

- `infer_su(b|per)levels` skips inferring involvement of sub-/super LNLs that are already present
- *(load)* Rename `skip_disk` to `use_github`
- *(query)* Rename `in_` to `isin` for `C` object

## [0.0.4] - 2024-10-11

### 🚀 Features

- [**breaking**] Make several helper functions private (e.g., `_max_likelihood()`)
- *(utils)* Add more shortname columns, like `surgery` for `("patient", "#", "neck_dissection")`
- *(load)* Allow search for datasets at different locations on disk
- *(query)* Add `C` object for easier `Q` creation
- *(query)* Add `in_` to `C` object
- *(validate)* Add `transform_to_lyprox` function

### 🐛 Bug Fixes

- *(load)* Resolve circular import of `_repo`

### 📚 Documentation

- Add intersphinx mapping to pandera
- Expand module docstrings
- Update `README.md` with library examples

### 🧪 Testing

- Fix failure due to changing order of items in set

### Change

- *(validate)* Add args to renamed validation
- Import useful stuff as top-level
- Make `main()` funcs private

### Remove

- *(load)* [**breaking**] `load_dataset()` not needed, one can just use `next(load_datasets())`

## [0.0.3] - 2024-10-01

### 🚀 Features

- Add method to infer sublevel involvement [#2]
- Add method to infer superlevel involvement [#2]
- *(load)* Allow loading from different repository and/or reference (tag, commit, ...) [#4]

### 🐛 Bug Fixes

- Make `align_diagnoses()` safer
- Make `combine()` method work as intended
- *(load)* Year may be equal to current year, not only smaller

### 📚 Documentation

- Make accessor method docstring more detailed
- Mention panda's `update()` in methods

### ⚙️ Miscellaneous Tasks

- Add documentation link to metadata
- Add changelog
- Remove pyright setting (where from?)
- Ignore B028 ruff rule

### Change

- Fix inconsistent method name

### Merge

- Branch '2-infer-sub-and-super-level-involvement' into 'dev'. Closes [#2]
- Branch '4-allow-loading-from-different-tagsrevisions' into 'dev'. Closes [#4]

### Refac

- Rename some temporary variables

### Remove

- *(load)* Unused defined error class

## [0.0.2] - 2024-09-27

### 🚀 Features

- Add some basic logging
- Add `percent` and `invert` to portion

### 📚 Documentation

- Ensure intersphinx links work

### 🧪 Testing

- Add doctest to `join_datasets()`

### ⚙️ Miscellaneous Tasks

- Update pre-commit hooks

### Build

- Remove dev deps

### Change

- Switch to pydantic for dataset definition
- Shorten accessor name to `ly`

### Refac

- Make load funcs/methods clean & consistent

## [0.0.1] - 2024-08-05

Initial implementation of the lyDATA library.

<!-- generated by git-cliff -->
<!-- markdownlint-disable-file MD024 -->

[0.2.3]: https://github.com/rmnldwg/lydata/compare/0.2.2..0.2.3
[0.2.2]: https://github.com/rmnldwg/lydata/compare/0.2.1..0.2.2
[0.2.1]: https://github.com/rmnldwg/lydata/compare/0.2.0..0.2.1
[0.2.0]: https://github.com/rmnldwg/lydata/compare/0.1.2..0.2.0
[0.1.2]: https://github.com/rmnldwg/lydata/compare/0.1.1..0.1.2
[0.1.1]: https://github.com/rmnldwg/lydata/compare/0.1.0..0.1.1
[0.1.0]: https://github.com/rmnldwg/lydata/compare/0.0.4..0.1.0
[0.0.4]: https://github.com/rmnldwg/lydata/compare/0.0.3..0.0.4
[0.0.3]: https://github.com/rmnldwg/lydata/compare/0.0.2..0.0.3
[0.0.2]: https://github.com/rmnldwg/lydata/compare/0.0.1..0.0.2
[0.0.1]: https://github.com/rmnldwg/lydata/compare/63b2d867888aa8f583c498ff3fc3f94cdb48765c..0.0.1

[#2]: https://github.com/rmnldwg/lydata/issues/2
[#4]: https://github.com/rmnldwg/lydata/issues/4
[#13]: https://github.com/rmnldwg/lydata/issues/13
