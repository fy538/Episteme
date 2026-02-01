"""
Custom management command to run Django with ASGI (uvicorn)

Usage: python manage.py runasgi [--host HOST] [--port PORT]
"""
import os
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run Django with ASGI server (uvicorn) for streaming support'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            default='127.0.0.1',
            help='Host to bind (default: 127.0.0.1)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port to bind (default: 8000)'
        )
        parser.add_argument(
            '--no-reload',
            action='store_true',
            help='Disable auto-reload on code changes'
        )

    def handle(self, *args, **options):
        host = options['host']
        port = options['port']
        reload_flag = not options['no_reload']

        self.stdout.write(
            self.style.SUCCESS(f'Starting ASGI server at http://{host}:{port}')
        )
        self.stdout.write('Quit the server with CONTROL-C.\n')

        try:
            import uvicorn
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    'uvicorn is not installed. Install with: pip install uvicorn'
                )
            )
            sys.exit(1)

        # Run uvicorn
        uvicorn.run(
            'config.asgi:application',
            host=host,
            port=port,
            reload=reload_flag,
            log_level='info',
        )
