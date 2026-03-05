#!/usr/bin/osascript
# Lists the wallpaper path currently showing on each desktop/space.
# Outputs one bare path per line; labels may be added by the caller.

set output to ""
tell application "System Events"
    set desktopList to every desktop
    repeat with i from 1 to count of desktopList
        set d to item i of desktopList
        set picPath to picture of d
        set output to output & picPath & linefeed
    end repeat
end tell
return output
