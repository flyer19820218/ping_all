-- Streamlit keep-alive using the normal Google Chrome profile on this Mac.
-- Sign in and complete two-step verification manually in Chrome once. This
-- script only refreshes existing tabs; it never handles credentials or MFA.

property targetURLs : {¬
    "https://financedailynews-mobile.streamlit.app/", ¬
    "https://financedailynews-web.streamlit.app/", ¬
    "https://finance-daily-news.streamlit.app/", ¬
    "https://bookmoney-web.streamlit.app/", ¬
    "https://scienceisveryeasy-diag.streamlit.app/", ¬
    "https://claappne-mobile.streamlit.app/", ¬
    "https://learning-diagnosis-web.streamlit.app/", ¬
    "https://scienceisveryeasy-mobile.streamlit.app/", ¬
    "https://thelast60days-ipad.streamlit.app/", ¬
    "https://thelast60days-web.streamlit.app/", ¬
    "https://tryagents-web.streamlit.app/"}

on refreshURL(targetURL)
    tell application "Google Chrome"
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

    end tell

    if didRefresh then return "refreshed " & targetURL
    return "skipped (open this app manually in Chrome first) " & targetURL
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

    -- Allow each normal Chrome navigation to start before visiting the next app.
    delay 5
end repeat

return my joinLines(results)
