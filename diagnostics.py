# diagnostics.py

import pygame
import logging

class Diagnostics:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(None, 30)

    def run_diagnostics(self):
        results = {}
        results['gpio'] = self.check_gpio()
        results['database'] = self.check_database()
        results['display'] = self.check_display()
        results['sound'] = self.check_sound()
        return results

    def check_gpio(self):
        try:
            # Test GPIO connections
            gpio_status = self.game.gpio_handler.test_connections()
            return {"status": "OK", "details": gpio_status}
        except Exception as e:
            logging.error(f"GPIO diagnostic error: {str(e)}")
            return {"status": "Error", "details": str(e)}

    def check_database(self):
        try:
            # Test database connection
            self.game.db.cursor.execute("SELECT 1")
            return {"status": "OK", "details": "Database connection successful"}
        except Exception as e:
            logging.error(f"Database diagnostic error: {str(e)}")
            return {"status": "Error", "details": str(e)}

    def check_display(self):
        try:
            # Check if display is initialized
            if self.game.screen:
                return {"status": "OK", "details": f"Display initialized: {self.game.screen.get_size()}"}
            else:
                return {"status": "Error", "details": "Display not initialized"}
        except Exception as e:
            logging.error(f"Display diagnostic error: {str(e)}")
            return {"status": "Error", "details": str(e)}

    def check_sound(self):
        try:
            # Check if sound is initialized
            if pygame.mixer.get_init():
                return {"status": "OK", "details": "Sound system initialized"}
            else:
                return {"status": "Error", "details": "Sound system not initialized"}
        except Exception as e:
            logging.error(f"Sound diagnostic error: {str(e)}")
            return {"status": "Error", "details": str(e)}

    def draw_diagnostic_screen(self, screen):
        screen.fill((0, 0, 0))
        results = self.run_diagnostics()
        y = 50
        for system, result in results.items():
            status_text = self.font.render(f"{system}: {result['status']}", True, (255, 255, 255))
            screen.blit(status_text, (50, y))
            details_text = self.font.render(result['details'], True, (200, 200, 200))
            screen.blit(details_text, (50, y + 30))
            y += 80
        pygame.display.flip()
