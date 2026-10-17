# Security

To report a vulnerability, use GitHub's private vulnerability reporting on this repository (Security tab, "Report a
vulnerability"). If that is not available, open an issue that says you have a security concern without including details, and
a private channel will be arranged.

The tools read local files and, for `esoi sheet-sync`, call the Google Sheets API with credentials you supply through the
environment. They do not send data anywhere else. Keep credential files out of the repository; `esoi hygiene` scans for them.
