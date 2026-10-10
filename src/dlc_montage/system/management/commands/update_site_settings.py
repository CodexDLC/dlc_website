import json

from codex_django.system.management.base_commands import BaseHashProtectedCommand
from django.conf import settings
from loguru import logger as log

from system.models.settings import SiteSettings


class Command(BaseHashProtectedCommand):
    """
    Management command to update Site Settings from JSON fixture.
    Checks a hash to avoid double loading.
    Usage: python manage.py update_site_settings
    """

    help = "Update Site Settings from JSON fixture (system/fixtures/content/site_settings.json)"
    fixture_key = "site_settings"

    def get_fixture_paths(self):
        return [settings.BASE_DIR / "system" / "fixtures" / "content" / "site_settings.json"]

    def handle_import(self, *args, **options):
        log.info("Command: update_site_settings | Action: Start")

        fixture_paths = self.get_fixture_paths()
        if not fixture_paths:
            return False

        fixture_path = fixture_paths[0]
        try:
            with open(fixture_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            log.error(f"Command: update_site_settings | Action: Failed | error=JSONDecodeError | message={e}")
            self.stdout.write(self.style.ERROR(f"Error decoding JSON: {e}"))
            return False

        if not data or not isinstance(data, list) or len(data) == 0:
            log.error("Command: update_site_settings | Action: Failed | error=Invalid format")
            self.stdout.write(self.style.ERROR("Invalid fixture format"))
            return False

        fixture_data = data[0]["fields"]

        # Load current settings using Singleton get() method
        site_settings = SiteSettings.load()

        # Compare and update
        updated_fields = []
        for field_name, new_value in fixture_data.items():
            if hasattr(site_settings, field_name):
                current_value = getattr(site_settings, field_name)

                # Convert Decimal fields to string for comparison
                if hasattr(current_value, "__str__") and field_name in ["latitude", "longitude"]:
                    current_value = str(current_value)

                if str(current_value) != str(new_value):
                    setattr(site_settings, field_name, new_value)
                    updated_fields.append(field_name)
                    log.debug(f"Action: FieldUpdate | field={field_name} | value={new_value}")
                    self.stdout.write(self.style.SUCCESS(f"  [UPDATE] {field_name}: {new_value}"))

        # Save if there are changes
        if updated_fields:
            site_settings.save()
            log.info(f"Command: update_site_settings | Action: SaveDB | count={len(updated_fields)}")

            from system.models.settings import get_site_settings_manager

            manager = get_site_settings_manager()
            manager.save_instance(site_settings)
            self.stdout.write(self.style.SUCCESS(f"\n✓ Site Settings updated ({len(updated_fields)} fields changed)"))
        else:
            log.info("Command: update_site_settings | Action: NoChanges")
            self.stdout.write(self.style.SUCCESS("\n✓ No changes needed (all fields up to date)"))

        log.info("Command: update_site_settings | Action: Success")
        return True
