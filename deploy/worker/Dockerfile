# Build the matching Django image first; both runtimes use the same immutable release.
ARG DLC_DJANGO_IMAGE
FROM ${DLC_DJANGO_IMAGE}

# The inherited HTTP probe does not apply to a management-command runtime.
HEALTHCHECK NONE
CMD ["python", "src/dlc_montage/manage.py", "sync_site_photos_worker", "--interval", "5"]
