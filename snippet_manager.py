import sublime
import sublime_plugin

import re
import os

try:
  from FileList.file_list import FileList
except ImportError as error:
  sublime.error_message("Dependency import failed; please read readme for " +
   "SnippetManager plugin for installation instructions; to disable this " +
   "message remove this plugin; message: " + str(error))
  raise error

# utility functions

def get_language(view):
  if len(view.sel()) == 0:
    return None

  scope = view.scope_name(view.sel()[0].a)

  match = None
  languages = []
  match = list(re.finditer('(source|text).(\w+)', scope))[-1]

  if match == None:
    return None

  available_languages = []
  for language in sublime.find_resources("*.tmLanguage"):
    file_name, _ = os.path.splitext(os.path.basename(language))
    available_languages.append(file_name.lower())

  for language in languages:
    if language not in available_languages:
      languages.remove(language)

  return match.group(1), match.group(2), set(languages)

def get_snippets_path(language = None):
  folder = sublime.packages_path() + '/User'
  if language != None:
    folder += '/' + language
  return folder

def get_snippets_files(languages = None):
  result = []
  path = get_snippets_path()
  for language in languages:
    for folder in os.listdir(path):
      if language != None and language != folder:
        continue

      language_folder = path + '/' + folder
      if not os.path.isdir(language_folder):
        continue

      for file in os.listdir(language_folder):
        snippet_file = language_folder + '/' + file
        name, extension = os.path.splitext(snippet_file)
        is_wrong_extension = (extension != '.sublime-snippet' and
          extension != '.sublime-snippet-enhanced')
        if is_wrong_extension:
          continue

        result.append(snippet_file)

  return result

def get_snippets(languages = None):
  files = get_snippets_files(languages)
  packages_path_len = len(sublime.packages_path()) + 1
  result = []

  for snippet in files:
    lang = os.path.basename(os.path.dirname(snippet))
    name, _ = os.path.splitext(os.path.basename(snippet))
    shortpath = snippet[packages_path_len:]
    header = name
    if languages == None:
      header = lang + ": " + header
    result.append([snippet, header, shortpath])

  return result

# open snippet

class ShowSnippetOpener(sublime_plugin.TextCommand):
  def run(self, edit, use_current_language = True, use_all_languages = False):
    self.use_current_language = use_current_language
    self.use_all_languages = use_all_languages
    list = FileList(self._get_snippets)
    list.show()

  def _get_snippets(self):
    language = None

    if self.use_current_language:
      info = get_language(self.view)
      if info == None:
        return []

      _, language, languages = info

    if not self.use_all_languages:
      languages = [language]

    return get_snippets(languages)

# create snippet

class State:
  def __init__(self):
    self.type = None
    self.language = None
    self.scope = None
    self.body = None
    self.view = None
    self.trigger = None

state = State()

class CreateSnippetFromSelection(sublime_plugin.TextCommand):
  def run(self, edit):
    type, language, _ = get_language(self.view)
    if language == None or self.view.sel()[0].a == self.view.sel()[0].b:
      return

    state.type = type
    state.language = language
    state.body = self.view.substr(self.view.sel()[0])

    name = re.sub(r'\W+', ' ', state.body.split("\n")[0]).lower()
    sublime.active_window().show_input_panel("Enter name of snippet (last " +
      "word is trigger)", name, self._on_enter, None, None)

  def _on_enter(self, value):
    if value == '':
      return

    state.trigger = re.search(r"([^\s]+)$", value).group(1)
    state.description = value[0:-len(state.trigger)].strip()
    folder = get_snippets_path(state.language)

    if not os.path.exists(folder):
      os.makedirs(folder)

    path = (folder + '/' + state.trigger + ' ' + state.description +
      '.sublime-snippet-enhanced')

    io = open(path, 'w')
    io.write('')
    io.close()

    state.view = sublime.active_window().open_file(path)

class LoadListener(sublime_plugin.EventListener):
  def on_load(self, view):
    if re.search(r'\.sublime-snippet(-enhanced)?$', view.file_name()) != None:
      view.settings().set('translate_tabs_to_spaces', False)

    cancel = state.view == None or \
      state.view.id() != view.id() or \
      view.substr(sublime.Region(0, view.size())) != ''

    if cancel:
      return

    snippet = "<snippet>\n" + \
      "\t<content><![CDATA[\n" + self.prepare_content(state.body) + \
      "$0\n]]></content>\n" + \
      "\t<tabTrigger>${1:" + self.prepare_content(state.trigger) + \
      "}</tabTrigger>\n" + \
      "\t<scope>" + \
      self.prepare_content(state.type) + "." + \
      self.prepare_content(state.language) + \
      "</scope>\n" + \
      "\t<description>${2:" + self.prepare_content(state.description) + \
      "}</description>\n" + \
      "</snippet>"

    view.run_command("insert_snippet", {"contents": snippet})

  def prepare_content(self, string):
    return string.replace('\\', '\\\\\\').replace('$', '\\\\\\$')

  # $asd + \qwe