# The one instruction every system that accepts an instruction receives, unchanged. It states German
# dictation conventions only and names nothing taken from a test set's references.
FORMATTING_INSTRUCTION = (
    "The audio is a German clinical dictation. Return the text as the written report, in German.\n"
    "1. Dictated punctuation and layout commands are instructions, not content. Replace each one "
    "with its symbol and remove the spoken word: Punkt -> . | Komma -> , | Doppelpunkt -> : | "
    "Strichpunkt or Semikolon -> ; | Fragezeichen -> ? | Klammer auf, Klammer zu -> ( ) | "
    "Schrägstrich -> / . For \"Neue Zeile\" start a new line. For \"Neuer Absatz\" or \"Neuer "
    "Abschnitt\" leave one empty line.\n"
    "2. Attach each punctuation mark directly to the word before it, and never output the same "
    "mark twice in a row.\n"
    "3. Write numbers as digits and dates as DD.MM.YYYY.\n"
    "4. Abbreviate units of measurement (Milligramm -> mg, Milliliter -> ml, Millimeter -> mm, "
    "Prozent -> %, Grad Celsius -> °C) and write \"pro\" between two units as \"/\" (mg/dl).\n"
    "5. Capitalise the first word after a full stop.\n"
    "6. Change nothing else: do not add, remove, reorder, translate or correct words, and do not "
    "add punctuation that was not dictated."
)
