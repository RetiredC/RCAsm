# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

import re
import shlex
import sys
from pathlib import Path
from typing import cast, List, Tuple

from PyQt5 import Qsci
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QToolBar, QAction, QPushButton,
                             QTabWidget, QLabel, QFrame, QShortcut, QSplitter, QMessageBox, QCheckBox, QComboBox,
                             QLineEdit)
from PyQt5.QtGui import QPainter, QColor, QKeySequence, QFontDatabase
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciStyle, QsciScintillaBase

import defs, utils, backup, compiler, lexer

########################################################################################################################

class CodeEditor(QsciScintilla):
    OCC_INDICATOR = 9  # choose any free indicator id (0..31)
    FIND_IND = 10
    def __init__(self, parent=None, IsLog: bool = False):
        super().__init__(parent)

        self.setUtf8(True)
        self.setTabWidth(4)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(True)
        self.setEolMode(QsciScintilla.EolUnix)
        self.convertEols(QsciScintilla.EolUnix)

        from PyQt5.QtGui import QFont
        if IsLog:
            font = QFont("Consolas", 8)
        else:
            font = QFont("Consolas", 11)
        self.setFont(font)
        self.setMarginsFont(font)
        self.setWrapMode(QsciScintilla.WrapNone)
        self.setScrollWidthTracking(True)
        
        if IsLog:
            self.setLexer(None)
            self.setPaper(QColor(150, 150, 150))
            self.setColor(QColor(0, 0, 0))
            self.setWrapMode(QsciScintilla.WrapWord)
        else:
            #syntax highlight
            lex = lexer.AsmLexer(self, font)

            #lex = QsciLexerPython(self)
            #lex.setDefaultFont(font)
            #lex.setDefaultPaper(QColor(200, 200, 200))
            #lex.setDefaultColor(QColor(0, 0, 0))
            self.setLexer(lex)

            #lines numbers
            self.setMarginType(0, QsciScintilla.NumberMargin)
            self.setMarginWidth(0, "0000")  #space for four digits
            self.setMarginsForegroundColor(QColor(0, 0, 0))
            self.setMarginsBackgroundColor(QColor(100, 100, 100))
            #advanced margin
            self.setMarginType(1, QsciScintilla.TextMargin)
            self.setMarginWidth(1, "0")
            self.setMarginSensitivity(1, True)  #margin clicks
            #self.marginClicked.connect(self.on_margin_clicked)
            self.user_margin_style = QsciStyle(
                100,  #just a style number
                "adv margin",  #desc
                QColor(0, 0, 0),  #font color
                QColor(150, 150, 150),  #background color for my margin
                font,
                eolFill=True,  #fill to end of line
            )

        self._init_indicator(self.OCC_INDICATOR, style=QsciScintillaBase.INDIC_ROUNDBOX, r=255, g=200, b=0)
        self._init_indicator(self.FIND_IND, style=QsciScintillaBase.INDIC_STRAIGHTBOX, r=0, g=180, b=255)
        self.selectionChanged.connect(self._highlight_selection_occurrences)
        self.textChanged.connect(self._highlight_selection_occurrences)
    @staticmethod
    def _rgb(r: int, g: int, b: int) -> int:
        # Scintilla uses COLORREF-like 0x00BBGGRR format
        return (r & 255) | ((g & 255) << 8) | ((b & 255) << 16)

    def _init_indicator(self, ind: int, style: int, r: int, g: int, b: int) -> None:
        bse = QsciScintillaBase
        self.SendScintilla(bse.SCI_INDICSETSTYLE, ind, style)
        self.SendScintilla(bse.SCI_INDICSETFORE, ind, self._rgb(r, g, b))
        self.SendScintilla(bse.SCI_INDICSETALPHA, ind, 70)
        self.SendScintilla(bse.SCI_INDICSETOUTLINEALPHA, ind, 200)
        self.SendScintilla(bse.SCI_INDICSETUNDER, ind, 1)

    def _clear_indicator(self, ind: int) -> None:
        bse = QsciScintillaBase
        doc_len = self.SendScintilla(bse.SCI_GETLENGTH)
        self.SendScintilla(bse.SCI_SETINDICATORCURRENT, ind)
        self.SendScintilla(bse.SCI_INDICATORCLEARRANGE, 0, doc_len)

    def _highlight_text_occurrences(
            self,
            text: str,
            ind: int,
            *,
            match_case: bool = True,
            whole_word: bool = False,
            max_len: int = 200,
    ) -> None:
        bse = QsciScintillaBase
        self._clear_indicator(ind)
        if not text:
            return
        # QScintilla uses U+2029 as line separator in selectedText()
        text = text.replace("\u2029", "\n")
        # Skip multi-line patterns
        if "\n" in text or "\r" in text:
            return
        # Skip whitespace-only patterns
        if text.strip() == "":
            return
        # Safety limit to avoid performance issues
        if len(text) > max_len:
            return
        flags = 0
        if match_case:
            flags |= bse.SCFIND_MATCHCASE
        if whole_word:
            flags |= bse.SCFIND_WHOLEWORD
        pat = text.encode("utf-8")
        pat_len = len(pat)
        doc_len = self.SendScintilla(bse.SCI_GETLENGTH)
        self.SendScintilla(bse.SCI_SETINDICATORCURRENT, ind)
        self.SendScintilla(bse.SCI_SETSEARCHFLAGS, flags)
        pos = 0
        while pos < doc_len:
            self.SendScintilla(bse.SCI_SETTARGETSTART, pos)
            self.SendScintilla(bse.SCI_SETTARGETEND, doc_len)
            found = self.SendScintilla(bse.SCI_SEARCHINTARGET, pat_len, pat)
            if found == -1:
                break
            self.SendScintilla(bse.SCI_INDICATORFILLRANGE, found, pat_len)
            pos = found + pat_len

    def _highlight_selection_occurrences(self) -> None:
        self._highlight_text_occurrences(self.selectedText(), self.OCC_INDICATOR, match_case=True, whole_word=False)

    def append_line(self, text: str) -> None:
        if not text.endswith("\n"):
            text += "\n"
        self.append(text)

    def get_line_text(self, line: int) -> str:
        if line < 0 or line >= self.lines():
            return ""
        return self.text(line)

    def get_line_count(self) -> int:
        return self.lines()


########################################################################################################################

class LeftBar(QWidget):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setFixedWidth(170)  #width
        # Fixed-width font for overlay text
        self.mono_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.mono_font.setPointSize(18)
        self.mono_font.setStretch(80)

    def paintEvent(self, event):
        painter = QPainter(self)

        # background
        painter.fillRect(self.rect(), QColor(60, 60, 60))

        # Prepare text drawing style once
        painter.setFont(self.mono_font)

        first_line = self.editor.firstVisibleLine()
        y = 0
        line = first_line

        # iterate visible lines
        while y < self.height() and line < self.editor.lines():
            line_height = self.editor.textHeight(line)
            s = self.editor.text(line).strip()
            cm = s.find("//")
            if cm >=0:
                s = s[:cm]
            ofs = 123
            if s.startswith("FUNCTION"):
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(100, 150, 100))
                painter.drawRect(1, y + 2, self.width() - 1, line_height - 4)

            if s.startswith("KERNEL"):
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(0, 255, 0))
                painter.drawRect(1, y + 2, self.width() - 1, line_height - 4)

            if s.startswith("CONST"):
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(50, 150, 255))
                painter.drawRect(1, y + 2, self.width() - 1, line_height - 4)

            if s.startswith("inc_func"):
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(180, 50, 50))
                painter.drawRect(ofs + 10, y + 2, 20, line_height - 4)

            if s.startswith("call_func"):
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(255, 50, 50))
                painter.drawRect(ofs + 10, y + 2, 20, line_height - 4)

            if s.startswith("."):
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(160, 80, 0))
                painter.drawRect(ofs + 15, y + 2, 15, line_height - 4)

            if s.startswith("["):
                painter.setPen(Qt.NoPen)
                if (s.find(" BRA") >= 0) or (s.find(" BRX") >= 0) or (s.find(" BRXU") >= 0):
                    painter.setBrush(QColor(255, 50, 255))
                    painter.drawRect(ofs + 35, y + 2, 10, line_height - 4)
                else:
                    painter.setBrush(QColor(0, 0, 180))
                    painter.drawRect(ofs + 41, y + 2, 4, line_height - 4)

                rw = "         "  # 2 + 5 + 2
                if len(s) > 20:
                    if (s[9] == "R") and (s[10] != "-"):
                        rw = utils.replace_str(rw, 0, "R" + s[10])
                    if (s[12] == "W") and (s[13] != "-"):
                        rw = utils.replace_str(rw, 7, "W" + s[13])
                    if (s[1] == "B") and (s[2:8] != "------"):
                        s2 = s[2:8]
                        s2 = s2.replace("-", "")
                        rw = utils.replace_str(rw, 4 - len(s2)//2, s2)

                painter.setPen(QColor(255, 255, 0))
                r = QRect(3, y, self.width() - 1, line_height)
                painter.drawText(r, Qt.AlignVCenter | Qt.AlignLeft, rw)

            y += line_height
            line += 1

########################################################################################################################

class EditorPage(QWidget):
    def __init__(self, file_name: str, parent=None):
        super().__init__(parent)

        self.file_name = file_name
        self.editor = CodeEditor(self,False)
        self.left_bar = LeftBar(self.editor, self)

        text = utils.load_str_from_file(self.file_name)
        text = "\n".join(line.rstrip(" \t") for line in text.splitlines()) #remove annoying right spaces
        self.editor.setText(text)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.left_bar)
        layout.addWidget(self.editor)

        self.editor.verticalScrollBar().valueChanged.connect(lambda _: self.left_bar.update())
        self.editor.textChanged.connect(self.left_bar.update)

    def save_file(self):
        utils.save_str_to_file(self.editor.text(), self.file_name)

########################################################################################################################

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setMinimumSize(1600, 900)

        utils.load_ide_options()
        if defs.WND_GEOMETRY is not None:
            self.restoreGeometry(defs.WND_GEOMETRY)
        else:
            self.resize(2400, 1200)

        #tabs
        self.tabs = QTabWidget()
        self.pages = []

        self.open_project()

        #editor on the right
        self.log_editor = CodeEditor(self, True)

        #splitter: left = tabs, right = editor
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.log_editor)
        #make left panel wider than right
        self.splitter.setStretchFactor(0, 3)  # tabs
        self.splitter.setStretchFactor(1, 2)  # right editor
        self.setCentralWidget(self.splitter)
        if defs.SPL_STATE is not None:
            self.splitter.restoreState(defs.SPL_STATE)

        #top toolbar
        toolbar = QToolBar("Main toolbar", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        #open button
        btn_open = QPushButton("Open Project")
        btn_open.clicked.connect(self.on_open_clicked)
        toolbar.addWidget(btn_open)
        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(self.on_open_clicked)

        #save button
        toolbar.addSeparator()
        btn_save = QPushButton("Save All")
        btn_save.clicked.connect(self.on_save_clicked)
        toolbar.addWidget(btn_save)
        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_save.activated.connect(self.on_save_clicked)

        toolbar.addSeparator()
        btn_run = QPushButton("Compile, Inject and Build")
        btn_run.clicked.connect(self.on_run_clicked)
        toolbar.addWidget(btn_run)
        shortcut_run = QShortcut(QKeySequence("F5"), self)
        shortcut_run.activated.connect(self.on_run_clicked)

        toolbar.addSeparator()
        self.cb_auto_compile = QCheckBox("Auto-Run")
        self.cb_auto_compile.setChecked(defs.AUTO_RUN)
        self.cb_auto_compile.toggled.connect(self.on_auto_compile_toggled)
        toolbar.addWidget(self.cb_auto_compile)

        toolbar.addSeparator()
        self.sm_combo = QComboBox()
        self.sm_combo.addItems(["SM89"])
        self.sm_combo.addItems(["SM120"])
        if defs.SM_VER == 89:
            self.sm_combo.setCurrentIndex(0)
        else:
            self.sm_combo.setCurrentIndex(1)

        self.sm_combo.currentIndexChanged.connect(self.on_sm_changed)
        toolbar.addWidget(self.sm_combo)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Find:"))
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Ctrl+R to reset")
        self.find_edit.setFixedWidth(150)
        self.find_edit.textChanged.connect(self.on_find_changed)
        toolbar.addWidget(self.find_edit)
        shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_find.activated.connect(self.on_ctrl_f)
        btn_clearfind = QPushButton("Reset")
        btn_clearfind.clicked.connect(self.on_btn_clearfind)
        toolbar.addWidget(btn_clearfind)
        shortcut_clearfind = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut_clearfind.activated.connect(self.on_btn_clearfind)
        toolbar.addSeparator()

        #status bar
        self.status = self.statusBar()

        self.msg_label = QLabel("Ready")
        self.msg_label.setFixedWidth(200)
        self.status.addWidget(self.msg_label)
        #self.status.addPermanentWidget(self.__make_separator())
        self.msg_issues = QLabel("---")
        self.status.addWidget(self.msg_issues, 1)

        self.pos_label = QLabel("")
        self.pos_label.setFixedWidth(300)
        self.status.addPermanentWidget(self.pos_label)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.a_label = QLabel("(c) RetiredCoder (check github)")
        self.a_label.setFixedWidth(300)
        self.status.addPermanentWidget(self.a_label)
        self.changed = False

    def open_project(self):
        self.files = utils.get_project_files(defs.PROJECT_PATH)
        for fn in self.files:
            page = EditorPage(fn, self)
            page.file_name = fn
            self.tabs.addTab(page, Path(fn).name)
            self.pages.append(page)
            page.editor.cursorPositionChanged.connect(self.on_cursor_pos_changed)
            page.editor.textChanged.connect(self.on_text_changed)
        self.setWindowTitle(f"RCAsm v1.0:     {Path(defs.PROJECT_PATH).resolve()}")

    def on_ctrl_f(self) -> None:
        self.find_edit.setFocus(Qt.ShortcutFocusReason)
        self.find_edit.selectAll()

    def on_find_changed(self, text: str) -> None:
        editor = self.get_current_editor()
        editor._highlight_text_occurrences(text, editor.FIND_IND, match_case=False, whole_word=False)

    def closeEvent(self, event):
        defs.WND_GEOMETRY = self.saveGeometry()
        defs.SPL_STATE = self.splitter.saveState()
        if not self.changed:
            utils.save_ide_options()
            event.accept()
            return
        reply = QMessageBox.question(
            self,
            "Unsaved changes",
            "There are unsaved changes.\n\nSave all modified files before exit?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.on_save_clicked()
            utils.save_ide_options()
            event.accept()
        elif reply == QMessageBox.No:
            utils.save_ide_options()
            event.accept()
        else:
            event.ignore()

    def __make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setLineWidth(1)
        return sep

    def get_current_page(self) -> EditorPage:
        widget = self.tabs.currentWidget()
        assert widget is not None
        return cast(EditorPage, widget)

    def get_current_file_name(self) -> str:
        return self.get_current_page().file_name

    def get_current_editor(self):
        return self.get_current_page().editor

    def collect_all_lines(self) -> List[Tuple[List[str], str]]:
        res: List[Tuple[List[str], str]] = []
        for page in self.pages:
            res.append((utils.PreprocessLines(page.editor.text().splitlines()), Path(page.file_name).name))
        return res

    def on_btn_clearfind(self):
        self.find_edit.setText("")

    def close_project(self) -> bool:
        if self.changed:
            reply = QMessageBox.question(
                self,
                "Unsaved changes",
                "There are unsaved changes.\n\nSave all modified files before closing?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.on_save_clicked()
                utils.save_ide_options()
            elif reply == QMessageBox.Cancel:
                return False
        self.tabs.blockSignals(True)
        try:
            while self.tabs.count() > 0:
                page = self.tabs.widget(0)
                # Optional: disconnect signals explicitly (not strictly required)
                try:
                    page.editor.cursorPositionChanged.disconnect(self.on_cursor_pos_changed)
                except Exception:
                    pass
                try:
                    page.editor.textChanged.disconnect(self.on_text_changed)
                except Exception:
                    pass
                self.tabs.removeTab(0)
                if page is not None:
                    page.setParent(None)  # Detach from tab widget
                    page.deleteLater()  # Safe Qt deletion
        finally:
            self.tabs.blockSignals(False)
        self.pages.clear()
        return True

    def on_open_clicked(self):
        folder = utils.select_folder(self, "Choose project folder", defs.PROJECT_PATH)
        if not folder:
            return
        if not self.close_project():
            return
        defs.PROJECT_PATH = folder
        self.open_project()


    def on_save_clicked(self):
        backup.save_backup(defs.PROJECT_PATH)
        for page in self.pages:
            page.save_file()
        self.changed = False
        self.msg_label.setText("Saved")

    def on_tab_changed(self, index: int):
        self.on_find_changed(self.find_edit.text())
        self.on_cursor_pos_changed(-1, -1)

    def on_cursor_pos_changed(self, line: int, col: int):
        line, col = self.get_current_editor().getCursorPosition()
        file_name = Path(self.get_current_file_name()).name
        s = f"{file_name}  |  Ln {line + 1}, Col {col + 1}"
        self.pos_label.setText(s)

    def on_text_changed(self):
        self.changed = True
        self.msg_label.setText("Changed")

    def on_run_clicked(self):
        utils.clear_log()
        err = compiler.compile_code(self.collect_all_lines(), True)
        if err:
            self.msg_issues.setText("SUCCESSFUL")
        else:
            self.msg_issues.setText("FAILED")
            return

        if self.cb_auto_compile.isChecked():
            lines:List[str] = []

            if defs.SM_VER == 120:
                args = shlex.split(defs.EXE_PARAMS120, posix=False)
            else:
                args = shlex.split(defs.EXE_PARAMS89, posix=False)

            compiler.run_exe(lines, args)
            for line in lines:
                utils.to_log(line)
            last = self.log_editor.lines() - 1
            if last < 0:
                return
            self.log_editor.ensureLineVisible(last)

    def on_auto_compile_toggled(self):
        defs.AUTO_RUN = self.cb_auto_compile.isChecked()

    def on_sm_changed(self, idx: int):
        if idx == 0:
            defs.SM_VER = 89
        else:
            defs.SM_VER = 120

        return None

########################################################################################################################

def run_editor():
    app = QApplication(sys.argv)
    win = MainWindow()
    utils.set_main_window(win)
    win.show()
    sys.exit(app.exec_())



