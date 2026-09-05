-- Streamlit keep-alive using the normal Safari profile on this Mac.
-- It never handles a password, cookie, Google login, or browser automation.

property targetURLs : {¬
    "https://financedailynews-mobile.streamlit.app/", ¬
    "https://financedailynews-web.streamlit.app/", ¬
    "https://lyu-science-cloud.streamlit.app/", ¬
    "https://ai-biology-lab.streamlit.app/", ¬
    "https://ai-earthscience-lab.streamlit.app/", ¬
    "https://finance-daily-news.streamlit.app/", ¬
    "https://science-truth-portal.streamlit.app/", ¬
    "https://science-ai-lab.streamlit.app/"}

on refreshURL(targetURL)
    tell application "Safari"
        set didRefresh to false

        -- Reuse a matching tab so the schedule does not create endless tabs.
        repeat with aWindow in windows
            repeat with aTab in tabs of aWindow
                try
                    set currentURL to URL of aTab
                    if currentURL starts with targetURL then
                        set URL of aTab to targetURL
                        set didRefresh to true
                        exit repeat
                    end if
                end try
            end repeat
            if didRefresh then exit repeat
        end repeat

        if not didRefresh then
            if (count of windows) is 0 then
                make new document with properties {URL:targetURL}
            else
                tell window 1 to make new tab with properties {URL:targetURL}
            end if
        end if
    end tell

    if didRefresh then return "refreshed " & targetURL
    return "opened " & targetURL
end refreshURL

on joinLines(lineList)
    set AppleScript's text item delimiters to linefeed
    set resultText to lineList as text
    set AppleScript's text item delimiters to ""
    return resultText
end joinLines

set results to {}
repeat with targetURL in targetURLs
    try
        set end of results to my refreshURL(contents of targetURL)
    on error errorMessage number errorNumber
        set end of results to "failed " & (contents of targetURL) & " (" & errorNumber & "): " & errorMessage
    end try

    -- Allow each normal Safari navigation to start before visiting the next app.
    delay 5
end repeat

return my joinLines(results)
