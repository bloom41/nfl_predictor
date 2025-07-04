"""
Django management command to start NFL news monitoring
"""
from django.core.management.base import BaseCommand
from nfl_api.news_monitor import NFLNewsMonitor, run_single_monitoring_cycle
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start NFL news and updates monitoring system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--single-run',
            action='store_true',
            help='Run a single monitoring cycle instead of continuous monitoring'
        )
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Run in test mode with verbose output'
        )

    def handle(self, *args, **options):
        single_run = options['single_run']
        test_mode = options['test_mode']

        if test_mode:
            logging.getLogger('nfl_api.news_monitor').setLevel(logging.DEBUG)

        self.stdout.write(
            self.style.SUCCESS('Starting NFL news monitoring system...')
        )

        try:
            if single_run:
                self.stdout.write('Running single monitoring cycle...')
                run_single_monitoring_cycle()
                self.stdout.write(
                    self.style.SUCCESS('Single monitoring cycle completed!')
                )
            else:
                self.stdout.write('Starting continuous monitoring...')
                self.stdout.write(
                    self.style.WARNING(
                        'This will run continuously. Press Ctrl+C to stop.'
                    )
                )
                
                monitor = NFLNewsMonitor()
                monitor.start_continuous_monitoring()

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS('\nMonitoring stopped by user.')
            )
        except Exception as e:
            logger.error(f'Error in news monitoring: {e}')
            self.stdout.write(
                self.style.ERROR(f'Monitoring failed: {e}')
            )