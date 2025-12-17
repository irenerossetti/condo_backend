from django.core.management.base import BaseCommand
from django.urls import get_resolver, resolve
from django.test import RequestFactory

class Command(BaseCommand):
    help = 'Test URL resolution'

    def handle(self, *args, **options):
        factory = RequestFactory()
        
        # Test URLs
        test_urls = [
            '/api/reports/test/',
            '/api/reports/advanced/',
            '/api/reports/export/',
        ]
        
        for url in test_urls:
            self.stdout.write(f"\nTesting: {url}")
            try:
                match = resolve(url)
                self.stdout.write(self.style.SUCCESS(f"  ✓ Resolved to: {match.func}"))
                self.stdout.write(f"    URL name: {match.url_name}")
                self.stdout.write(f"    View class: {match.func.view_class if hasattr(match.func, 'view_class') else 'N/A'}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed: {e}"))
        
        # List all patterns
        self.stdout.write("\n\nAll URL patterns:")
        resolver = get_resolver()
        for pattern in resolver.url_patterns:
            self.stdout.write(f"  - {pattern.pattern}")
