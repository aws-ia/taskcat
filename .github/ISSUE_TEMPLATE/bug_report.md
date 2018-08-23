---
name: Bug report
about: Template to report bugs

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Are you testing a *QuickStart* or *Custom template*?
2. Attach or link a copy of the template if possible (**remove any sensitive info**)
3. Provide the parameters that you passed. (**remove any sensitive info**) 
4. How did you install taskcat? (docker or pip3)
5. Are you using a *profile*, *an instance role* or  *access keys* to run taskcat?
6. Is your AWS environment configured via `aws configure`?

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Version (Please make sure you are running the latest version of taskcat)
 - Taskcat Version (ex: [2018.817.210357])

 Note: Python Version (python3 required)

To find versions:
*Via taskcat*: `taskcat -V`
*Via pip3*: `pip3 show taskcat`

Note: both version should match

To update taskcat run:
 *for docker* : `docker pull taskcat/taskcat`
 *for pip3*: `pip3 install --upgrade taskcat`

**Additional context**
Add any other context about the problem here.
