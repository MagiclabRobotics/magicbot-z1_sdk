#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import queue
import signal
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import magicbot_z1_python as magicbot


# All GaitMode values exposed by the SDK (see magic_type.h).
GAIT_MODE_NAMES = [
    "GAIT_PASSIVE",
    "GAIT_RECOVERY_STAND",
    "GAIT_BALANCE_STAND",
    "GAIT_HUMANOID_WALK",
    "GAIT_LOWLEVL_SDK",
    "GAIT_HYBRID_SDK",
]

APP_BG = "#eef2f7"
CARD_BG = "#ffffff"
HEADER_BG = "#172554"
HEADER_FG = "#f8fafc"
MUTED_FG = "#64748b"
DARK_PANEL_BG = "#0f172a"
DARK_PANEL_FG = "#e2e8f0"


class RobotVizApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MagicBot Z1 Control Panel")
        self.root.geometry("1220x860")
        self.root.minsize(1080, 760)

        self.robot = None
        self.audio = None
        self.motion = None
        self.monitor = None
        self.slam = None
        self.running = True

        self.log_queue = queue.Queue()
        self.intent_queue = queue.Queue()

        self.local_ip_var = tk.StringVar(value="192.168.54.111")
        self.connect_status_var = tk.StringVar(value="Disconnected")
        self.battery_var = tk.StringVar(value="-")
        self.health_var = tk.StringVar(value="-")
        self.power_var = tk.StringVar(value="-")
        self.battery_state_var = tk.StringVar(value="-")

        self.volume_var = tk.StringVar(value="50")
        self.tts_id_var = tk.StringVar(value="")
        self.tts_var = tk.StringVar(value="How's the weather today!")
        self.tts_priority_var = tk.StringVar(value="HIGH")
        self.tts_mode_var = tk.StringVar(value="CLEARTOP")
        self.tts_timeout_var = tk.StringVar(value="10000")
        self.dialog_var = tk.StringVar(value="Hello, how can I help you?")
        self.trick_var = tk.StringVar(value="ACTION_WELCOME")
        self.gait_var = tk.StringVar(value="GAIT_BALANCE_STAND")
        self.current_gait_var = tk.StringVar(value="-")
        self.head_angle_var = tk.StringVar(value="0.0")
        self.auto_refresh_on_connect_var = tk.BooleanVar(value=False)
        self.map_name_var = tk.StringVar(value="map_demo")
        self.map_path_var = tk.StringVar(value="")
        self.pose_x_var = tk.StringVar(value="0.0")
        self.pose_y_var = tk.StringVar(value="0.0")
        self.pose_yaw_var = tk.StringVar(value="0.0")
        self.target_x_var = tk.StringVar(value="0.0")
        self.target_y_var = tk.StringVar(value="0.0")
        self.target_yaw_var = tk.StringVar(value="0.0")

        self._build_ui()
        self._start_event_loop()

        signal.signal(signal.SIGINT, self._on_sigint)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        self._setup_style()

        header = ttk.Frame(self.root, style="Header.TFrame", padding=(18, 14))
        header.pack(fill=tk.X)
        ttk.Label(header, text="MagicBot Z1 Control Panel", style="Header.Title.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Label(header, text="Audio | Motion | Monitor | SLAM", style="Header.Subtitle.TLabel").pack(
            side=tk.RIGHT
        )

        top = ttk.LabelFrame(self.root, text="Connection", padding=12, style="Card.TLabelframe")
        top.pack(fill=tk.X, padx=14, pady=(12, 8))

        ttk.Label(top, text="Local IP").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.local_ip_var, width=18).pack(side=tk.LEFT, padx=(8, 10))
        ttk.Button(top, text="Connect", command=self.connect_robot, style="Accent.TButton").pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(top, text="Disconnect", command=self.disconnect_robot, style="Danger.TButton").pack(
            side=tk.LEFT, padx=4
        )
        ttk.Label(top, text="Status:").pack(side=tk.LEFT, padx=(16, 4))
        self.connect_status_label = ttk.Label(top, textvariable=self.connect_status_var, style="Status.Bad.TLabel")
        self.connect_status_label.pack(side=tk.LEFT)

        body = ttk.Frame(self.root, padding=(14, 0))
        body.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(body)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.audio_tab = ttk.Frame(notebook, padding=12)
        self.motion_tab = ttk.Frame(notebook, padding=12)
        self.monitor_tab = ttk.Frame(notebook, padding=12)
        self.slam_tab = ttk.Frame(notebook, padding=12)

        notebook.add(self.audio_tab, text="Audio")
        notebook.add(self.motion_tab, text="High-Level Motion")
        notebook.add(self.monitor_tab, text="Monitor")
        notebook.add(self.slam_tab, text="SLAM & Navigation")

        self._build_audio_tab()
        self._build_motion_tab()
        self._build_monitor_tab()
        self._build_slam_tab()

        log_frame = ttk.LabelFrame(self.root, text="Logs", padding=10, style="Card.TLabelframe")
        log_frame.pack(fill=tk.BOTH, expand=False, padx=14, pady=(6, 14))
        self.log_text = ScrolledText(log_frame, height=12, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self._style_log_text(self.log_text)

    def _setup_style(self):
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        self.root.configure(background=APP_BG)
        style.configure("TFrame", background=APP_BG)
        style.configure("Header.TFrame", background=HEADER_BG)
        style.configure(
            "Header.Title.TLabel",
            background=HEADER_BG,
            foreground=HEADER_FG,
            font=("TkDefaultFont", 16, "bold"),
        )
        style.configure(
            "Header.Subtitle.TLabel",
            background=HEADER_BG,
            foreground="#bfdbfe",
            font=("TkDefaultFont", 10),
        )
        style.configure("TLabelframe", background=APP_BG)
        style.configure("Card.TLabelframe", background=CARD_BG, borderwidth=1, relief=tk.SOLID)
        style.configure(
            "TLabelframe.Label",
            background=APP_BG,
            foreground="#0f172a",
            font=("TkDefaultFont", 10, "bold"),
        )
        style.configure("TLabel", background=APP_BG, foreground="#1e293b")
        style.configure("Hint.TLabel", background=APP_BG, foreground=MUTED_FG)
        style.configure("TEntry", padding=(4, 3))
        style.configure("TButton", padding=(10, 5), font=("TkDefaultFont", 9))
        style.configure(
            "Accent.TButton",
            background="#2563eb",
            foreground="#ffffff",
            padding=(12, 5),
        )
        style.configure(
            "Danger.TButton",
            background="#dc2626",
            foreground="#ffffff",
            padding=(12, 5),
        )
        style.configure("TCheckbutton", background=APP_BG, foreground="#334155")
        style.configure("TNotebook", background=APP_BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 8), font=("TkDefaultFont", 9, "bold"))
        style.map(
            "TNotebook.Tab",
            background=[("selected", CARD_BG), ("active", "#dbeafe")],
            foreground=[("selected", "#1d4ed8"), ("active", "#1e3a8a")],
        )
        style.configure(
            "Status.Good.TLabel",
            background="#dcfce7",
            foreground="#166534",
            padding=(10, 4),
            font=("TkDefaultFont", 10, "bold"),
        )
        style.configure(
            "Status.Bad.TLabel",
            background="#fee2e2",
            foreground="#991b1b",
            padding=(10, 4),
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("pressed", "#1e40af")])
        style.map("Danger.TButton", background=[("active", "#b91c1c"), ("pressed", "#991b1b")])

    def _build_audio_tab(self):
        ttk.Label(
            self.audio_tab,
            text="Speech, wakeup and dialog controls.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        volume_frame = ttk.LabelFrame(self.audio_tab, text="Volume", padding=8)
        volume_frame.pack(fill=tk.X, pady=4)
        row1 = ttk.Frame(volume_frame)
        row1.pack(fill=tk.X, pady=4)
        ttk.Label(row1, text="Volume").pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.volume_var, width=8).pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="Get Volume", command=self.get_volume).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="Set Volume", command=self.set_volume).pack(side=tk.LEFT, padx=4)

        tts_frame = ttk.LabelFrame(self.audio_tab, text="Text To Speech", padding=8)
        tts_frame.pack(fill=tk.X, pady=4)
        row2 = ttk.Frame(tts_frame)
        row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="TTS").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.tts_var, width=40).pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text="Play TTS", command=self.play_tts).pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="Stop TTS", command=self.stop_tts).pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(tts_frame)
        row3.pack(fill=tk.X, pady=4)
        ttk.Label(row3, text="TTS id").pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.tts_id_var, width=20).pack(side=tk.LEFT, padx=6)
        ttk.Label(row3, text="Priority").pack(side=tk.LEFT)
        ttk.Combobox(
            row3,
            values=["HIGH", "MIDDLE", "LOW"],
            textvariable=self.tts_priority_var,
            width=10,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)
        ttk.Label(row3, text="Mode").pack(side=tk.LEFT)
        ttk.Combobox(
            row3,
            values=["CLEARTOP", "ADD", "CLEARBUFFER"],
            textvariable=self.tts_mode_var,
            width=12,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)
        ttk.Label(row3, text="Timeout(ms)").pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.tts_timeout_var, width=10).pack(side=tk.LEFT, padx=4)

        row3b = ttk.Frame(tts_frame)
        row3b.pack(fill=tk.X, pady=4)
        ttk.Label(row3b, text="Dialog text").pack(side=tk.LEFT)
        ttk.Entry(row3b, textvariable=self.dialog_var, width=48).pack(side=tk.LEFT, padx=6)
        ttk.Button(row3b, text="Start Dialog", command=self.start_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3b, text="Stop Dialog", command=self.stop_dialog).pack(side=tk.LEFT, padx=4)

        stream_frame = ttk.LabelFrame(self.audio_tab, text="Audio Streams", padding=10)
        stream_frame.pack(fill=tk.X, pady=6)
        for column in range(3):
            stream_frame.columnconfigure(column, weight=1, uniform="audio_streams")

        audio_stream = ttk.LabelFrame(stream_frame, text="Audio Stream", padding=8)
        audio_stream.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=2)
        self._stream_button_grid(
            audio_stream,
            [
                ("Open", self.open_audio_stream),
                ("Close", self.close_audio_stream),
                ("Subscribe", self.subscribe_audio_stream),
                ("Unsubscribe", self.unsubscribe_audio_stream),
            ],
        )

        wakeup_stream = ttk.LabelFrame(stream_frame, text="Wakeup Stream", padding=8)
        wakeup_stream.grid(row=0, column=1, sticky="nsew", padx=6, pady=2)
        self._stream_button_grid(
            wakeup_stream,
            [
                ("Open", self.open_wakeup_stream),
                ("Close", self.close_wakeup_stream),
                ("Subscribe", self.subscribe_wakeup),
                ("Unsubscribe", self.unsubscribe_wakeup),
            ],
        )

        dialog_stream = ttk.LabelFrame(stream_frame, text="Dialog Intent", padding=8)
        dialog_stream.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=2)
        self._stream_button_grid(
            dialog_stream,
            [
                ("Subscribe", self.subscribe_dialog_intent),
                ("Unsubscribe", self.unsubscribe_dialog_intent),
            ],
        )

    def _build_motion_tab(self):
        ttk.Label(
            self.motion_tab,
            text="Posture, trick actions and joystick movement.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        posture_frame = ttk.LabelFrame(self.motion_tab, text="Posture", padding=8)
        posture_frame.pack(fill=tk.X, pady=4)
        row1 = ttk.Frame(posture_frame)
        row1.pack(fill=tk.X, pady=4)
        ttk.Label(row1, text="Gait").pack(side=tk.LEFT)
        ttk.Combobox(
            row1,
            values=GAIT_MODE_NAMES,
            textvariable=self.gait_var,
            width=28,
            state="readonly",
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="Set Gait", command=self.set_gait).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="Get Current Gait", command=self.get_current_gait).pack(side=tk.LEFT, padx=4)
        row1b = ttk.Frame(posture_frame)
        row1b.pack(fill=tk.X, pady=2)
        ttk.Label(row1b, text="Current gait").pack(side=tk.LEFT)
        ttk.Entry(row1b, textvariable=self.current_gait_var, width=40, state="readonly").pack(
            side=tk.LEFT, padx=6
        )
        row1c = ttk.Frame(posture_frame)
        row1c.pack(fill=tk.X, pady=4)
        ttk.Button(row1c, text="Recovery Stand", command=self.recovery_stand).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1c, text="Balance Stand", command=self.balance_stand).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1c, text="Humanoid Walk", command=self.humanoid_walk).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1c, text="Passive", command=self.passive_gait).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1c, text="Hybrid SDK", command=self.hybrid_sdk_gait).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1c, text="Low-Level SDK", command=self.low_level_sdk_gait).pack(side=tk.LEFT, padx=4)

        trick_frame = ttk.LabelFrame(self.motion_tab, text="Trick Action", padding=8)
        trick_frame.pack(fill=tk.X, pady=4)
        row2 = ttk.Frame(trick_frame)
        row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="Trick").pack(side=tk.LEFT)
        tricks = [
            "ACTION_NONE",
            "ACTION_SHAKE_LEFT_HAND_REACHOUT",
            "ACTION_SHAKE_LEFT_HAND_WITHDRAW",
            "ACTION_SHAKE_RIGHT_HAND_REACHOUT",
            "ACTION_SHAKE_RIGHT_HAND_WITHDRAW",
            "ACTION_WELCOME",
            "ACTION_CHE_GUAN_SUO",
            "ACTION_LEFT_GREETING",
            "ACTION_RIGHT_GREETING",
            "ACTION_SHAKE_HEAD",
            "ACTION_TRUN_LEFT_INTRODUCE_HIGH",
            "ACTION_TRUN_LEFT_INTRODUCE_LOW",
            "ACTION_TRUN_RIGHT_INTRODUCE_HIGH",
            "ACTION_TRUN_RIGHT_INTRODUCE_LOW",
            "ACTION_FLY_KISS_LEFT",
            "ACTION_FLY_KISS_RIGHT",
            "ACTION_SUPERMAN_WAVE",
            "ACTION_CLAP_HAND",
            "ACTION_HOLD_CERT_REACHOUT",
            "ACTION_HOLD_CERT_WITHDRAW",
            "ACTION_HUG_REACHOUT",
            "ACTION_HUG_WITHDRAW",
            "ACTION_TRUN_WAVE_LEFT",
            "ACTION_TRUN_WAVE_RIGHT",
            "ACTION_RIGHT_HAND_SALUTE",
        ]
        ttk.Combobox(row2, values=tricks, textvariable=self.trick_var, width=40, state="readonly").pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text="Execute Trick", command=self.execute_trick).pack(side=tk.LEFT, padx=4)

        row3 = ttk.LabelFrame(self.motion_tab, text="Joystick Motion", padding=8)
        row3.pack(fill=tk.X, pady=8)
        ttk.Button(row3, text="Forward", command=lambda: self.joystick(0.0, 1.0, 0.0, 0.0)).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Backward", command=lambda: self.joystick(0.0, -1.0, 0.0, 0.0)).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Left", command=lambda: self.joystick(-1.0, 0.0, 0.0, 0.0)).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Right", command=lambda: self.joystick(1.0, 0.0, 0.0, 0.0)).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Turn Left", command=lambda: self.joystick(0.0, 0.0, -1.0, 0.0)).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Turn Right", command=lambda: self.joystick(0.0, 0.0, 1.0, 0.0)).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="Stop", command=lambda: self.joystick(0.0, 0.0, 0.0, 0.0)).pack(side=tk.LEFT, padx=4)

        head_frame = ttk.LabelFrame(self.motion_tab, text="Head Control", padding=8)
        head_frame.pack(fill=tk.X, pady=8)
        row4 = ttk.Frame(head_frame)
        row4.pack(fill=tk.X, pady=4)
        ttk.Label(row4, text="Head angle").pack(side=tk.LEFT)
        ttk.Entry(row4, textvariable=self.head_angle_var, width=10).pack(side=tk.LEFT, padx=6)
        ttk.Button(row4, text="Move Head", command=self.head_move).pack(side=tk.LEFT, padx=4)
        ttk.Button(row4, text="Reset Head", command=lambda: self._run(self.motion.head_move, 0.0, 10000, tag="head_move_reset")).pack(side=tk.LEFT, padx=4)

    def _build_monitor_tab(self):
        ttk.Label(
            self.monitor_tab,
            text="Power status and fault inspection.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        actions = ttk.LabelFrame(self.monitor_tab, text="State Refresh", padding=8)
        actions.pack(fill=tk.X, pady=4)
        row1 = ttk.Frame(actions)
        row1.pack(fill=tk.X, pady=4)
        ttk.Button(row1, text="Refresh State", command=self.refresh_state).pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="Auto Refresh (1s)", command=self.toggle_auto_refresh).pack(side=tk.LEFT, padx=4)
        self.auto_btn_ref = row1.winfo_children()[-1]
        self.auto_refresh = False
        ttk.Checkbutton(
            row1,
            text="Auto refresh after connect",
            variable=self.auto_refresh_on_connect_var,
        ).pack(side=tk.LEFT, padx=10)

        grid = ttk.LabelFrame(self.monitor_tab, text="Robot State", padding=8)
        grid.pack(fill=tk.X, pady=8)
        self._state_row(grid, 0, "Battery %", self.battery_var)
        self._state_row(grid, 1, "Battery Health", self.health_var)
        self._state_row(grid, 2, "Battery State", self.battery_state_var)
        self._state_row(grid, 3, "Power Supply", self.power_var)

        faults_frame = ttk.LabelFrame(self.monitor_tab, text="Faults", padding=8)
        faults_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.faults_text = ScrolledText(faults_frame, height=12, state=tk.DISABLED, wrap=tk.WORD)
        self.faults_text.pack(fill=tk.BOTH, expand=True)
        self._style_plain_text(self.faults_text)

    def _build_slam_tab(self):
        ttk.Label(
            self.slam_tab,
            text="Mapping, localization and navigation workflows.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        map_cfg = ttk.LabelFrame(self.slam_tab, text="Map Parameters", padding=8)
        map_cfg.pack(fill=tk.X, pady=4)
        ttk.Label(map_cfg, text="Map name").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(map_cfg, textvariable=self.map_name_var, width=24).grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(map_cfg, text="Map path").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Entry(map_cfg, textvariable=self.map_path_var, width=48).grid(row=0, column=3, sticky="w", padx=4, pady=2)
        ttk.Button(map_cfg, text="Get Map Path", command=self.get_map_path).grid(row=0, column=4, padx=6, pady=2)

        mapping_flow = ttk.LabelFrame(self.slam_tab, text="Mapping Flow (Step-by-step)", padding=8)
        mapping_flow.pack(fill=tk.X, pady=6)
        ttk.Button(mapping_flow, text="1) Recovery Stand", command=self.recovery_stand).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_flow, text="2) Balance Stand", command=self.balance_stand).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_flow, text="3) Activate Mapping Mode", command=self.activate_mapping_mode).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_flow, text="4) Start Mapping", command=self.start_mapping).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_flow, text="5) Save Map", command=self.save_map).pack(side=tk.LEFT, padx=4)

        mapping_tools = ttk.LabelFrame(self.slam_tab, text="Mapping Tools", padding=8)
        mapping_tools.pack(fill=tk.X, pady=6)
        ttk.Button(mapping_tools, text="Cancel Mapping", command=self.cancel_mapping).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_tools, text="Load Map", command=self.load_map).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_tools, text="Delete Map", command=self.delete_map).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_tools, text="Get All Map Info", command=self.get_all_map_info).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_tools, text="Get Point Cloud Map", command=self.get_point_cloud_map).pack(side=tk.LEFT, padx=4)
        ttk.Button(mapping_tools, text="Close SLAM", command=self.close_slam).pack(side=tk.LEFT, padx=4)

        loc_cfg = ttk.LabelFrame(self.slam_tab, text="Localization / Navigation Parameters", padding=8)
        loc_cfg.pack(fill=tk.X, pady=6)
        ttk.Label(loc_cfg, text="Init pose x/y/yaw").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(loc_cfg, textvariable=self.pose_x_var, width=8).grid(row=0, column=1, padx=2, pady=2)
        ttk.Entry(loc_cfg, textvariable=self.pose_y_var, width=8).grid(row=0, column=2, padx=2, pady=2)
        ttk.Entry(loc_cfg, textvariable=self.pose_yaw_var, width=8).grid(row=0, column=3, padx=2, pady=2)
        ttk.Label(loc_cfg, text="Target x/y/yaw").grid(row=0, column=4, sticky="w", padx=10, pady=2)
        ttk.Entry(loc_cfg, textvariable=self.target_x_var, width=8).grid(row=0, column=5, padx=2, pady=2)
        ttk.Entry(loc_cfg, textvariable=self.target_y_var, width=8).grid(row=0, column=6, padx=2, pady=2)
        ttk.Entry(loc_cfg, textvariable=self.target_yaw_var, width=8).grid(row=0, column=7, padx=2, pady=2)

        nav_flow = ttk.LabelFrame(self.slam_tab, text="Navigation Flow (Step-by-step)", padding=8)
        nav_flow.pack(fill=tk.X, pady=6)
        ttk.Button(nav_flow, text="1) Activate Localization", command=self.activate_localization_mode).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_flow, text="2) Init Pose", command=self.init_pose).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_flow, text="3) Get Localization Info", command=self.get_localization_info).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_flow, text="4) Activate Navigation", command=self.activate_navigation_mode).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_flow, text="5) Set Nav Target", command=self.set_nav_target).pack(side=tk.LEFT, padx=4)

        nav_tools = ttk.LabelFrame(self.slam_tab, text="Navigation Tools", padding=8)
        nav_tools.pack(fill=tk.X, pady=6)
        ttk.Button(nav_tools, text="Pause Nav", command=self.pause_nav).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_tools, text="Resume Nav", command=self.resume_nav).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_tools, text="Cancel Nav", command=self.cancel_nav).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_tools, text="Get Nav Status", command=self.get_nav_status).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_tools, text="Close Navigation", command=self.close_navigation).pack(side=tk.LEFT, padx=4)

        odom_tools = ttk.LabelFrame(self.slam_tab, text="Odometry", padding=8)
        odom_tools.pack(fill=tk.X, pady=6)
        ttk.Button(odom_tools, text="Open Odom Stream", command=self.open_odom_stream).pack(side=tk.LEFT, padx=4)
        ttk.Button(odom_tools, text="Close Odom Stream", command=self.close_odom_stream).pack(side=tk.LEFT, padx=4)
        ttk.Button(odom_tools, text="Subscribe Odom", command=self.subscribe_odom).pack(side=tk.LEFT, padx=4)
        ttk.Button(odom_tools, text="Unsubscribe Odom", command=self.unsubscribe_odom).pack(side=tk.LEFT, padx=4)

    @staticmethod
    def _state_row(parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(parent, textvariable=var, font=("TkDefaultFont", 10, "bold")).grid(
            row=row, column=1, sticky="w", padx=4, pady=2
        )

    @staticmethod
    def _stream_button_grid(parent, buttons):
        for column in range(2):
            parent.columnconfigure(column, weight=1, uniform="stream_buttons")

        for index, (text, command) in enumerate(buttons):
            ttk.Button(parent, text=text, command=command).grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=4,
                pady=4,
            )

    @staticmethod
    def _style_plain_text(widget: ScrolledText):
        widget.configure(
            background=CARD_BG,
            foreground="#0f172a",
            insertbackground="#0f172a",
            borderwidth=0,
            relief=tk.FLAT,
            padx=10,
            pady=8,
            font=("TkFixedFont", 10),
        )

    @staticmethod
    def _style_log_text(widget: ScrolledText):
        widget.configure(
            background=DARK_PANEL_BG,
            foreground=DARK_PANEL_FG,
            insertbackground=DARK_PANEL_FG,
            borderwidth=0,
            relief=tk.FLAT,
            padx=10,
            pady=8,
            font=("TkFixedFont", 10),
        )
        widget.tag_configure("timestamp", foreground="#94a3b8")
        widget.tag_configure("success", foreground="#86efac")
        widget.tag_configure("warning", foreground="#fde68a")
        widget.tag_configure("error", foreground="#fca5a5")
        widget.tag_configure("default", foreground=DARK_PANEL_FG)

    def _start_event_loop(self):
        self.root.after(100, self._drain_queues)

    def _drain_queues(self):
        while not self.log_queue.empty():
            self._append_log(self.log_queue.get_nowait())
        while not self.intent_queue.empty():
            intent = self.intent_queue.get_nowait()
            self._append_log(f"[dialog_intent] {intent}")
        self.root.after(100, self._drain_queues)

    def _append_log(self, message: str):
        ts = time.strftime("%H:%M:%S")
        message_lower = message.lower()
        if "failed" in message_lower or "exception" in message_lower or "invalid" in message_lower:
            tag = "error"
        elif "disabled" in message_lower or "required" in message_lower or "disconnected" in message_lower:
            tag = "warning"
        elif "success" in message_lower or "connected" in message_lower:
            tag = "success"
        else:
            tag = "default"

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _log(self, message: str):
        self.log_queue.put(message)

    def _on_sigint(self, *_):
        self.on_close()

    def _run(self, func, *args, tag="op", callback=None):
        def worker():
            try:
                result = func(*args)
                if callback:
                    callback(result)
                else:
                    if hasattr(result, "code"):
                        if result.code == magicbot.ErrorCode.OK:
                            self._log(f"{tag}: success")
                        else:
                            self._log(f"{tag}: failed code={result.code}, msg={result.message}")
            except Exception as exc:
                self._log(f"{tag}: exception {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_connected(self):
        if self.robot is None:
            self._log("Please connect robot first.")
            return False
        return True

    def _parse_float(self, value: str, name: str):
        try:
            return float(value)
        except ValueError:
            self._log(f"{name}: invalid float value")
            return None

    def connect_robot(self):
        if self.robot is not None:
            self._log("Robot already connected.")
            return

        def worker():
            try:
                self.robot = magicbot.MagicRobot()
                ip = self.local_ip_var.get().strip()
                if not self.robot.initialize(ip):
                    self._log("initialize failed")
                    self.robot.shutdown()
                    self.robot = None
                    return
                status = self.robot.connect()
                if status.code != magicbot.ErrorCode.OK:
                    self._log(f"connect failed: {status.message}")
                    self.robot.shutdown()
                    self.robot = None
                    return

                self.audio = self.robot.get_audio_controller()
                self.motion = self.robot.get_high_level_motion_controller()
                self.monitor = self.robot.get_state_monitor()
                self.slam = self.robot.get_slam_nav_controller()

                if not self.audio.initialize():
                    self._log("audio initialize failed")
                if self.robot.set_motion_control_level(magicbot.ControllerLevel.HighLevel).code != magicbot.ErrorCode.OK:
                    self._log("set motion control level HighLevel failed")
                if not self.motion.initialize():
                    self._log("high-level motion initialize failed")
                if not self.monitor.initialize():
                    self._log("state monitor initialize failed")
                if not self.slam.initialize():
                    self._log("slam navigation initialize failed")

                self.connect_status_var.set("Connected")
                self.connect_status_label.configure(style="Status.Good.TLabel")
                self._log("Robot connected and controllers initialized.")
                if self.auto_refresh_on_connect_var.get():
                    if not self.auto_refresh:
                        self.toggle_auto_refresh()
                    else:
                        self.refresh_state()
            except Exception as exc:
                self._log(f"connect exception: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def disconnect_robot(self):
        if self.robot is None:
            return
        try:
            try:
                self.audio.unsubscribe_dialog_intent()
            except Exception:
                pass
            try:
                self.monitor.shutdown()
            except Exception:
                pass
            try:
                self.slam.shutdown()
            except Exception:
                pass
            try:
                self.motion.shutdown()
            except Exception:
                pass
            try:
                self.audio.shutdown()
            except Exception:
                pass
            try:
                self.robot.disconnect()
            except Exception:
                pass
            try:
                self.robot.shutdown()
            except Exception:
                pass
        finally:
            self.robot = None
            self.audio = None
            self.motion = None
            self.monitor = None
            self.slam = None
            self.connect_status_var.set("Disconnected")
            self.connect_status_label.configure(style="Status.Bad.TLabel")
            self._log("Robot disconnected.")

    def on_close(self):
        if not self.running:
            return
        self.running = False
        self.disconnect_robot()
        self.root.quit()
        self.root.destroy()

    # Audio actions
    def get_volume(self):
        if not self._ensure_connected():
            return

        def cb(result):
            status, volume = result
            if status.code == magicbot.ErrorCode.OK:
                self._log(f"get_volume: {volume}")
                self.volume_var.set(str(volume))
            else:
                self._log(f"get_volume failed: {status.message}")

        self._run(self.audio.get_volume, tag="get_volume", callback=cb)

    def set_volume(self):
        if not self._ensure_connected():
            return
        try:
            volume = int(self.volume_var.get())
        except ValueError:
            self._log("set_volume: invalid number")
            return
        self._run(self.audio.set_volume, volume, tag=f"set_volume({volume})")

    def play_tts(self):
        if not self._ensure_connected():
            return
        try:
            timeout_ms = int(self.tts_timeout_var.get())
        except ValueError:
            self._log("play_tts: invalid timeout")
            return
        tts = magicbot.TtsCommand()
        tts_id = self.tts_id_var.get().strip()
        tts.id = tts_id if tts_id else str(int(time.time() * 1000))
        tts.content = self.tts_var.get().strip() or "Hello"
        tts.priority = getattr(magicbot.TtsPriority, self.tts_priority_var.get(), magicbot.TtsPriority.HIGH)
        tts.mode = getattr(magicbot.TtsMode, self.tts_mode_var.get(), magicbot.TtsMode.CLEARTOP)
        self._run(self.audio.play, tts, timeout_ms, tag="play_tts")

    def stop_tts(self):
        if not self._ensure_connected():
            return
        self._run(self.audio.stop, tag="stop_tts")

    def start_dialog(self):
        if not self._ensure_connected():
            return
        self._run(self.audio.start_dialog, self.dialog_var.get().strip(), tag="start_dialog")

    def stop_dialog(self):
        if not self._ensure_connected():
            return
        self._run(self.audio.stop_dialog, tag="stop_dialog")

    def open_audio_stream(self):
        if not self._ensure_connected():
            return
        self._run(self.audio.open_audio_stream, tag="open_audio_stream")

    def close_audio_stream(self):
        if not self._ensure_connected():
            return
        self._run(self.audio.close_audio_stream, tag="close_audio_stream")

    def subscribe_audio_stream(self):
        if not self._ensure_connected():
            return
        try:
            self.audio.subscribe_origin_audio_stream(lambda x: None)
            self.audio.subscribe_bf_audio_stream(lambda x: None)
            self._log("subscribe_audio_stream: success")
        except Exception as exc:
            self._log(f"subscribe_audio_stream exception: {exc}")

    def unsubscribe_audio_stream(self):
        if not self._ensure_connected():
            return
        try:
            self.audio.unsubscribe_origin_audio_stream()
            self.audio.unsubscribe_bf_audio_stream()
            self._log("unsubscribe_audio_stream: success")
        except Exception as exc:
            self._log(f"unsubscribe_audio_stream exception: {exc}")

    def open_wakeup_stream(self):
        if not self._ensure_connected():
            return
        self._run(self.audio.open_wakeup_status_stream, tag="open_wakeup_stream")

    def close_wakeup_stream(self):
        if not self._ensure_connected():
            return
        self._run(self.audio.close_wakeup_status_stream, tag="close_wakeup_stream")

    def subscribe_wakeup(self):
        if not self._ensure_connected():
            return
        try:
            self.audio.subscribe_wakeup_status(
                lambda s: self._log(f"wakeup: is_wakeup={s.is_wakeup}, orient={getattr(s, 'wakeup_orientation', 0.0):.2f}")
            )
            self._log("subscribe_wakeup: success")
        except Exception as exc:
            self._log(f"subscribe_wakeup exception: {exc}")

    def unsubscribe_wakeup(self):
        if not self._ensure_connected():
            return
        try:
            self.audio.unsubscribe_wakeup_status()
            self._log("unsubscribe_wakeup: success")
        except Exception as exc:
            self._log(f"unsubscribe_wakeup exception: {exc}")

    def subscribe_dialog_intent(self):
        if not self._ensure_connected():
            return
        try:
            self.audio.subscribe_dialog_intent(lambda d: self.intent_queue.put(d.intent))
            self._log("subscribe_dialog_intent: success")
        except Exception as exc:
            self._log(f"subscribe_dialog_intent exception: {exc}")

    def unsubscribe_dialog_intent(self):
        if not self._ensure_connected():
            return
        try:
            self.audio.unsubscribe_dialog_intent()
            self._log("unsubscribe_dialog_intent: success")
        except Exception as exc:
            self._log(f"unsubscribe_dialog_intent exception: {exc}")

    # High-level motion actions
    @staticmethod
    def _resolve_gait_mode(gait_name: str):
        return getattr(magicbot.GaitMode, gait_name, None)

    @staticmethod
    def _format_gait_mode(gait_mode) -> str:
        for name in GAIT_MODE_NAMES:
            if getattr(magicbot.GaitMode, name) == gait_mode:
                return f"{name} ({int(gait_mode)})"
        return str(gait_mode)

    def _set_gait_mode(self, gait_mode, tag: str):
        if not self._ensure_connected():
            return
        self._run(self.motion.set_gait, gait_mode, 10000, tag=tag)

    def set_gait(self):
        if not self._ensure_connected():
            return
        gait_name = self.gait_var.get()
        gait_mode = self._resolve_gait_mode(gait_name)
        if gait_mode is None:
            self._log(f"set_gait: unknown gait {gait_name}")
            return
        self._set_gait_mode(gait_mode, f"set_gait({gait_name})")

    def get_current_gait(self):
        if not self._ensure_connected():
            return

        def cb(result):
            status, gait_mode = result
            if status.code != magicbot.ErrorCode.OK:
                self._log(f"get_gait: failed code={status.code}, msg={status.message}")
                return
            text = self._format_gait_mode(gait_mode)
            self.current_gait_var.set(text)
            self._log(f"get_gait: {text}")

        self._run(self.motion.get_gait, tag="get_gait", callback=cb)

    def recovery_stand(self):
        self.gait_var.set("GAIT_RECOVERY_STAND")
        self._set_gait_mode(magicbot.GaitMode.GAIT_RECOVERY_STAND, "recovery_stand")

    def balance_stand(self):
        self.gait_var.set("GAIT_BALANCE_STAND")
        self._set_gait_mode(magicbot.GaitMode.GAIT_BALANCE_STAND, "balance_stand")

    def humanoid_walk(self):
        self.gait_var.set("GAIT_HUMANOID_WALK")
        self._set_gait_mode(magicbot.GaitMode.GAIT_HUMANOID_WALK, "humanoid_walk")

    def passive_gait(self):
        self.gait_var.set("GAIT_PASSIVE")
        self._set_gait_mode(magicbot.GaitMode.GAIT_PASSIVE, "passive_gait")

    def hybrid_sdk_gait(self):
        self.gait_var.set("GAIT_HYBRID_SDK")
        self._set_gait_mode(magicbot.GaitMode.GAIT_HYBRID_SDK, "hybrid_sdk_gait")

    def low_level_sdk_gait(self):
        self.gait_var.set("GAIT_LOWLEVL_SDK")
        self._set_gait_mode(magicbot.GaitMode.GAIT_LOWLEVL_SDK, "low_level_sdk_gait")

    def execute_trick(self):
        if not self._ensure_connected():
            return
        trick_name = self.trick_var.get()
        trick = getattr(magicbot.TrickAction, trick_name, magicbot.TrickAction.ACTION_NONE)
        self._run(self.motion.execute_trick, trick, 10000, tag=f"execute_trick({trick_name})")

    def joystick(self, lx, ly, rx, ry):
        if not self._ensure_connected():
            return
        cmd = magicbot.JoystickCommand()
        cmd.left_x_axis = lx
        cmd.left_y_axis = ly
        cmd.right_x_axis = rx
        cmd.right_y_axis = ry
        self._run(self.motion.send_joystick_command, cmd, tag=f"joystick({lx},{ly},{rx},{ry})")

    def head_move(self):
        if not self._ensure_connected():
            return
        try:
            angle = float(self.head_angle_var.get())
        except ValueError:
            self._log("head_move: invalid angle")
            return
        self._run(self.motion.head_move, angle, 10000, tag=f"head_move({angle})")

    # Monitor actions
    def refresh_state(self):
        if not self._ensure_connected():
            return

        def cb(result):
            status, state = result
            if status.code != magicbot.ErrorCode.OK:
                self._log(f"refresh_state failed: {status.message}")
                return
            self.battery_var.set(str(state.bms_data.battery_percentage))
            self.health_var.set(str(state.bms_data.battery_health))
            self.battery_state_var.set(str(state.bms_data.battery_state))
            self.power_var.set(str(state.bms_data.power_supply_status))

            self.faults_text.configure(state=tk.NORMAL)
            self.faults_text.delete("1.0", tk.END)
            if not state.faults:
                self.faults_text.insert(tk.END, "No faults\n")
            else:
                for item in state.faults:
                    self.faults_text.insert(tk.END, f"code={item.error_code}, msg={item.error_message}\n")
            self.faults_text.configure(state=tk.DISABLED)
            self._log("refresh_state: success")

        self._run(self.monitor.get_current_state, tag="refresh_state", callback=cb)

    def toggle_auto_refresh(self):
        self.auto_refresh = not self.auto_refresh
        self.auto_btn_ref.configure(text="Auto Refresh (stop)" if self.auto_refresh else "Auto Refresh (1s)")
        if self.auto_refresh:
            self._log("auto_refresh enabled")
            self._auto_refresh_loop()
        else:
            self._log("auto_refresh disabled")

    def _auto_refresh_loop(self):
        if not self.auto_refresh or not self.running:
            return
        self.refresh_state()
        self.root.after(1000, self._auto_refresh_loop)

    # SLAM & Navigation actions
    def activate_mapping_mode(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.activate_slam_mode, magicbot.SlamMode.MAPPING, "", 10000, tag="activate_mapping_mode")

    def start_mapping(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.start_mapping, 10000, tag="start_mapping")

    def cancel_mapping(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.cancel_mapping, 10000, tag="cancel_mapping")

    def save_map(self):
        if not self._ensure_connected():
            return
        map_name = self.map_name_var.get().strip()
        if not map_name:
            self._log("save_map: map name required")
            return
        self._run(self.slam.save_map, map_name, 20000, tag=f"save_map({map_name})")

    def load_map(self):
        if not self._ensure_connected():
            return
        map_name = self.map_name_var.get().strip()
        if not map_name:
            self._log("load_map: map name required")
            return
        self._run(self.slam.load_map, map_name, 10000, tag=f"load_map({map_name})")

    def delete_map(self):
        if not self._ensure_connected():
            return
        map_name = self.map_name_var.get().strip()
        if not map_name:
            self._log("delete_map: map name required")
            return
        self._run(self.slam.delete_map, map_name, 10000, tag=f"delete_map({map_name})")

    def get_all_map_info(self):
        if not self._ensure_connected():
            return

        def cb(result):
            status, info = result
            if status.code != magicbot.ErrorCode.OK:
                self._log(f"get_all_map_info failed: {status.message}")
                return
            names = [m.map_name for m in info.map_infos]
            self._log(f"get_all_map_info: current={info.current_map_name}, maps={names}")

        self._run(self.slam.get_all_map_info, 10000, tag="get_all_map_info", callback=cb)

    def get_map_path(self):
        if not self._ensure_connected():
            return
        map_name = self.map_name_var.get().strip()
        if not map_name:
            self._log("get_map_path: map name required")
            return

        def cb(result):
            status, paths = result
            if status.code != magicbot.ErrorCode.OK:
                self._log(f"get_map_path failed: {status.message}")
                return
            if paths:
                self.map_path_var.set(paths[0])
            self._log(f"get_map_path({map_name}): {paths}")

        self._run(self.slam.get_map_path, map_name, 10000, tag=f"get_map_path({map_name})", callback=cb)

    def get_point_cloud_map(self):
        if not self._ensure_connected():
            return

        def cb(result):
            status, point_cloud = result
            if status.code != magicbot.ErrorCode.OK:
                self._log(f"get_point_cloud_map failed: {status.message}")
                return
            self._log(
                f"get_point_cloud_map: width={point_cloud.width}, height={point_cloud.height}, bytes={len(point_cloud.data)}"
            )

        self._run(self.slam.get_point_cloud_map, 10000, tag="get_point_cloud_map", callback=cb)

    def close_slam(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.activate_slam_mode, magicbot.SlamMode.IDLE, "", 10000, tag="close_slam")

    def activate_localization_mode(self):
        if not self._ensure_connected():
            return
        map_path = self.map_path_var.get().strip()
        if not map_path:
            self._log("activate_localization_mode: map path required")
            return
        self._run(self.slam.activate_slam_mode, magicbot.SlamMode.LOCALIZATION, map_path, 10000, tag="activate_localization_mode")

    def init_pose(self):
        if not self._ensure_connected():
            return
        x = self._parse_float(self.pose_x_var.get(), "pose_x")
        y = self._parse_float(self.pose_y_var.get(), "pose_y")
        yaw = self._parse_float(self.pose_yaw_var.get(), "pose_yaw")
        if x is None or y is None or yaw is None:
            return
        pose = magicbot.Pose3DEuler()
        pose.position = [x, y, 0.0]
        pose.orientation = [0.0, 0.0, yaw]
        self._run(self.slam.init_pose, pose, 10000, tag=f"init_pose({x},{y},{yaw})")

    def get_localization_info(self):
        if not self._ensure_connected():
            return

        def cb(result):
            status, info = result
            if status.code != magicbot.ErrorCode.OK:
                self._log(f"get_localization_info failed: {status.message}")
                return
            self._log(
                "localization: ok=%s pos=%s yaw=%.3f"
                % (info.is_localization, list(info.pose.position), info.pose.orientation[2])
            )

        self._run(self.slam.get_current_localization_info, tag="get_localization_info", callback=cb)

    def activate_navigation_mode(self):
        if not self._ensure_connected():
            return
        map_path = self.map_path_var.get().strip()
        if not map_path:
            self._log("activate_navigation_mode: map path required")
            return
        self._run(self.slam.activate_nav_mode, magicbot.NavMode.GRID_MAP, map_path, 10000, tag="activate_navigation_mode")

    def set_nav_target(self):
        if not self._ensure_connected():
            return
        x = self._parse_float(self.target_x_var.get(), "target_x")
        y = self._parse_float(self.target_y_var.get(), "target_y")
        yaw = self._parse_float(self.target_yaw_var.get(), "target_yaw")
        if x is None or y is None or yaw is None:
            return
        target = magicbot.NavTarget()
        target.id = 1
        target.frame_id = "map"
        target.goal.position = [x, y, 0.0]
        target.goal.orientation = [0.0, 0.0, yaw]
        self._run(self.slam.set_nav_target, target, 10000, tag=f"set_nav_target({x},{y},{yaw})")

    def pause_nav(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.pause_nav_task, 10000, tag="pause_nav")

    def resume_nav(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.resume_nav_task, 10000, tag="resume_nav")

    def cancel_nav(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.cancel_nav_task, 10000, tag="cancel_nav")

    def get_nav_status(self):
        if not self._ensure_connected():
            return

        def cb(result):
            status, nav_status = result
            if status.code != magicbot.ErrorCode.OK:
                self._log(f"get_nav_status failed: {status.message}")
                return
            self._log(
                f"nav_status: id={nav_status.id}, status={nav_status.status}, error={nav_status.error_code}, desc={nav_status.error_desc}"
            )

        self._run(self.slam.get_nav_task_status, tag="get_nav_status", callback=cb)

    def close_navigation(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.activate_nav_mode, magicbot.NavMode.IDLE, "", 10000, tag="close_navigation")

    def open_odom_stream(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.open_odometry_stream, 10000, tag="open_odom_stream")

    def close_odom_stream(self):
        if not self._ensure_connected():
            return
        self._run(self.slam.close_odometry_stream, 10000, tag="close_odom_stream")

    def subscribe_odom(self):
        if not self._ensure_connected():
            return
        try:
            self.slam.subscribe_odometry(
                lambda odom: self._log(
                    f"odom: pos=({odom.position[0]:.2f},{odom.position[1]:.2f},{odom.position[2]:.2f}) "
                    f"lin=({odom.linear_velocity[0]:.2f},{odom.linear_velocity[1]:.2f},{odom.linear_velocity[2]:.2f})"
                )
            )
            self._log("subscribe_odom: success")
        except Exception as exc:
            self._log(f"subscribe_odom exception: {exc}")

    def unsubscribe_odom(self):
        if not self._ensure_connected():
            return
        try:
            self.slam.unsubscribe_odometry()
            self._log("unsubscribe_odom: success")
        except Exception as exc:
            self._log(f"unsubscribe_odom exception: {exc}")


def main():
    root = tk.Tk()
    app = RobotVizApp(root)
    app._log(f"Robot model: {magicbot.get_robot_model()}")
    root.mainloop()


if __name__ == "__main__":
    main()

