#!/usr/bin/env sh

# Set up and configure layout and touch screen for 7 inch TFT display
xrandr --output eDP-1 --right-of HDMI-2
xrandr --output HDMI-2 --rotate left
xrandr --output HDMI-2 --primary
xinput map-to-output "深圳市全动电子技术有限公司 ByQDtech 触控USB鼠标" HDMI-2
