"""
Texts for the commands feature.
All user-visible texts are served via i18n FTL files:
  resources/locales/{lang}/welcome.ftl

FTL keys used:
  welcome-user    — welcome message for regular users
  welcome-admin   — welcome message for admins
  welcome-btn-launch — launch button
  welcome-btn-admin  — admin panel button

Access pattern in UI:
  i18n.welcome.user(name=name)
  i18n.welcome.admin(name=name)
  i18n.welcome.btn.launch()
  i18n.welcome.btn.admin()
"""
