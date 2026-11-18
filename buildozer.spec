[app]
title = YoRacer
package.name = yoracer
package.domain = org.yoracer

source.dir = .
source.include_exts = py,png
version = 1.0.0

requirements = python3,pygame

orientation = portrait
fullscreen = 1
icon.filename = %(source.dir)s/icon.png

android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
