import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, GObject, Gdk
import os
from subprocess import Popen, PIPE
import threading

class ProcessWindow(Gtk.Window):
    def __init__(self, processPath):
        Gtk.Window.__init__(self, title="Process Output Console")
        #Variables needed for obtaining and displaying process output
        self.p = None
        self.proc_complete = False
        self.curr_out_buff_pos = 0
        self.curr_read_buff_pos = 0
        self.curr_out_buff = []
        #Configuraiton for this Gtk.Window
        self.set_default_size(250, 180)
        self.set_resizable(True)
        self.connect("destroy", self.destroy_progress)
        self.set_title("Process Output Console")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_size_request(600, 180)
        self.set_border_width(8)
        #Create the VBox in case we want to add additional items later
        self.vbox = Gtk.VBox(False, 5)
        self.vbox.set_border_width(10)
        self.add(self.vbox)
        self.vbox.show()
        #create the scrolled window
        self.scrolled_window =Gtk.ScrolledWindow()
        #self.scrolled_window.set_usize(460, 100)
        self.vbox.add(self.scrolled_window)
        self.scrolled_window.show()
        self.text_view = Gtk.TextView()
        self.msg_i = 0
        self.text_buffer = self.text_view.get_buffer()
        self.scrolled_window.add_with_viewport(self.text_view)
        self.text_view.connect("size-allocate", self.autoscroll)
        self.text_view.show()
        #Show the window
        self.show_all()
        #Start the thread that executes the process and captures its output
        t = threading.Thread(target=self.watchProcess, args=(processPath,))
        t.start()
        #Start a timer that will retrieve the process output and show it on the TextView
        GObject.timeout_add(100, self.appendText)

    def autoscroll(self, *args):
        #The actual scrolling method
        adj = self.scrolled_window.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def watchProcess(self, processPath):
        #Function for starting the process and capturing its stdout
        try:
            self.curr_out_buff.append("Starting process: " + str(processPath) + "\r\n")
            self.curr_out_buff_pos = self.curr_out_buff_pos + 1
            self.p = Popen(processPath, shell=False, stdout=PIPE, bufsize=1)
            with self.p.stdout:
                for line in iter(self.p.stdout.readline, b''):
                    if line.rstrip().lstrip() != "":
                        self.curr_out_buff.append(line)
                        self.curr_out_buff_pos = self.curr_out_buff_pos + 1
            # wait for the subprocess to exit
            self.p.wait()
            #Need to set proc_complete so that the appendText method can return False
            #and then subsequently, this will stop the GObject timer
            self.proc_complete = True
        except Exception as x:
            print "Something went wrong while running process: " + str(processPath) + "\r\n" + str(x)
            if self.p != None and self.p.poll() == None:
                self.p.terminate()
            self.destroy()
            exit()

    def destroy_progress(self, widget, data=None):
        #Sharing thread memory, so we have access to the process that it creates and watches
        #if the process is still running, terminate it
        if self.p != None and self.p.poll() == None:
            self.p.terminate()
        self.destroy()
        exit()

    def appendText(self):
        #This function is called by a GObject timer. It will check if there is
        #any new output from the executing process. If there is data then
        #it will be pulled from the buffer and displayed in the Text View
        #If the process has stopped, then an additional check is conducted
        #to ensure the final output is displayed
        if self.curr_out_buff_pos > self.curr_read_buff_pos:
            i = self.text_buffer.get_end_iter()
            for x in xrange(self.curr_read_buff_pos, self.curr_out_buff_pos):
                #print "GOOD reading",self.curr_out_buff[x]
                self.text_buffer.insert(i, str(self.curr_out_buff[x]), -1)
            self.curr_read_buff_pos = self.curr_out_buff_pos
        if self.proc_complete != True:
            return True
        else:
            while self.curr_out_buff_pos > self.curr_read_buff_pos:
                i = self.text_buffer.get_end_iter()
                for x in xrange(self.curr_read_buff_pos, self.curr_out_buff_pos):
                    self.text_buffer.insert(i, str(self.curr_out_buff[x]), -1)
                self.curr_read_buff_pos = self.curr_out_buff_pos
            i = self.text_buffer.get_end_iter()
            self.text_buffer.insert(i, str("Process execution complete"), -1)
            return False

if __name__ == "__main__":
     a = ProcessWindow("ping localhost -t")
     Gtk.main()
