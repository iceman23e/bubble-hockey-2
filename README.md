# bubble-hockey-2

to install:
```
curl -sSL https://raw.githubusercontent.com/iceman23e/bubble_hockey_2/main/install.sh | bash
```
Make updator executable:
```
chmod +x check_updates.sh
```
```
bubble_hockey/
├── assets/
│   ├── fonts/
│   │   ├── Perfect DOS VGA 437.ttf
│   │   ├── PressStart2P-Regular.ttf
│   │   ├── VCR_OSD_MONO_1.001.ttf
│   │   └── Pixellari.ttf
│   ├── images/
│   │   ├── volcano_idle.png
│   │   ├── volcano_eruption_frames/
│   │   │   └── frame_0.png
│   │   │   └── frame_1.png
│   │   │   └── ...
│   │   ├── lava_flow_frames/
│   │   │   └── frame_0.png
│   │   │   └── frame_1.png
│   │   │   └── ...
│   ├── sounds/
│   │   ├── period_start.wav
│   │   ├── period_end.wav
│   │   ├── goal_scored.wav
│   │   ├── countdown_timer.wav
│   │   ├── taunt_1.wav
│   │   ├── lucky_shot.wav
│   │   ├── goalie_interference.wav
│   │   ├── power_play.wav
│   │   ├── momentum_shift.wav
│   │   └── button_click.wav
│   └── themes/
│       ├── default/
│       │   ├── images/
│       │   ├── sounds/
│       │   └── fonts/
│       └── ...
├── database/
│   └── bubble_hockey.db
├── logs/
│   └── game.log
├── main.py
├── game.py
├── settings.py
├── database.py
├── web_server.py
├── utils.py
├── templates/
│   ├── index.html
│   ├── game.html
│   ├── settings.html
│   ├── system_settings.html
│   └── theme_manager.html
├── requirements.txt
└── install.sh
```
