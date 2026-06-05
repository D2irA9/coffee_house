from globals import *
import sys

def game(screen, events, station_manager):
    py.display.set_caption("Кофейня")
    for event in events:
        if event.type == py.QUIT:
            db.close()
            py.quit()
            sys.exit()

    station_manager.handle_events(events)
    station_manager.draw(screen)
