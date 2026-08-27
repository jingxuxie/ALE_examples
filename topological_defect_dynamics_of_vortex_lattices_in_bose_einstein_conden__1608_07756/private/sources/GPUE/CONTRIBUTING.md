# Contributing to GPUE

GPUE is primarly developed for scientific applications on high-performance computing systems.
As such, all submissions will be expected to run on various Linux-based hardware with a focus on performance and usability.

If there are any questions related to the current status of GPUE, please refer to the [documentation](https://gpue-group.github.io/).

## Bug reports and issues

If any problem arises while using GPUE code, please open an issue in the [primary fork of GPUE](https://github.com/GPUE-group/GPUE).
There are four general issue labels to use:

1. Physical inaccuracies -- These are considered breaking bugs and will be addressed immediately.
2. Usability issues -- These are problems running GPUE, ranging from compilation errors to problems with equation parsing. These are also considered breaking bugs and will be addressed according to the severity of the problem.
3. General problem -- any issue that is not related to physical inaccuracies or usability. These will be addressed depending on severity and submission date.
4. Feature request -- These are for anything we are missing in GPUE and will be addressed based on novelty and utility.

## Pull requests

If you wish to submit code via Pull Request (PR) directly to GPUE, please first create an issue, as outlined above.
All four previously defined labels apply to PRs.
Please refer to the corresponding issues in PRs.

All PRs will be tested with the `gpue -u` command and if the PR intends to create a new feature, this feature must be tested with a function in the `src/unit_test.cu` file.

In addition, if the PR is sufficiently advanced (as indicated by previous contributors) please update the [documentation](https://gpue-group.github.io/) accordingly with the contents of the PR.

### Style guide

There is no formal style guide for GPUE, but it follows standard conventions for CUDA programming, favoring C-style syntax when possible.
Each PR should have the appropriate Doxygen formatting and each feature PR will be reviewed on overall performance and usability.


# Code Of Conduct
## Our Pledge

In the interest of fostering an open and welcoming environment, we as contributors and maintainers pledge to making participation in our project and our community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.
Our Standards

## Examples of behavior that contributes to creating a positive environment include:

    Using welcoming and inclusive language
    Being respectful of differing viewpoints and experiences
    Gracefully accepting constructive criticism
    Focusing on what is best for the community
    Showing empathy towards other community members

## Examples of unacceptable behavior by participants include:

- The use of sexualized language or imagery and unwelcome sexual attention or advances
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others’ private information, such as a physical or electronic address, without explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional setting

## Our Responsibilities

Project maintainers are responsible for clarifying the standards of acceptable behavior and are expected to take appropriate and fair corrective action in response to any instances of unacceptable behavior.

Project maintainers have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned to this Code of Conduct, or to ban temporarily or permanently any contributor for other behaviors that they deem inappropriate, threatening, offensive, or harmful.

## Scope

This Code of Conduct applies both within project spaces and in public spaces when an individual is representing the project or its community. Examples of representing a project or community include using an official project e-mail address, posting via an official social media account, or acting as an appointed representative at an online or offline event. Representation of a project may be further defined and clarified by project maintainers.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team at [loriordan@gmail.com]. All complaints will be reviewed and investigated and will result in a response that is deemed necessary and appropriate to the circumstances. The project team is obligated to maintain confidentiality with regard to the reporter of an incident. Further details of specific enforcement policies may be posted separately.

Project maintainers who do not follow or enforce the Code of Conduct in good faith may face temporary or permanent repercussions as determined by other members of the project’s leadership.
Attribution

This Code of Conduct is adapted from the Contributor Covenant, version 1.4, available at https://www.contributor-covenant.org/version/1/4/code-of-conduct.html

For answers to common questions about this code of conduct, see https://www.contributor-covenant.org/faq
