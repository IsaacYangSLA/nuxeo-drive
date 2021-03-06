import os
import time
import sys

from nxdrive.client import LocalClient
from shutil import copyfile
from nxdrive.tests.common_unit_test import UnitTestCase
from nose.plugins.skip import SkipTest


class TestWindows(UnitTestCase):

    def test_local_replace(self):
        raise SkipTest("WIP in https://jira.nuxeo.com/browse/NXDRIVE-170")
        local = LocalClient(self.local_test_folder_1)
        remote = self.remote_document_client_1
        self.engine_1.start()
        self.wait_sync()

        # Create 2 files with the same name but different content
        # in separate folders
        local.make_file('/', 'test.odt', 'Some content.')
        local.make_folder('/', 'folder')
        copyfile(os.path.join(self.local_test_folder_1, 'test.odt'),
                 os.path.join(self.local_test_folder_1, 'folder', 'test.odt'))
        local.update_content('/folder/test.odt', 'Updated content.')

        # Copy the newest file to the root workspace and synchronize it
        sync_root = os.path.join(self.local_nxdrive_folder_1,
                                 self.workspace_title)
        test_file = os.path.join(self.local_test_folder_1, 'folder',
                                 'test.odt')
        copyfile(test_file, os.path.join(sync_root, 'test.odt'))
        self.wait_sync()
        self.assertTrue(remote.exists('/test.odt'))
        self.assertEquals(remote.get_content('/test.odt'), 'Updated content.')

        # Copy the oldest file to the root workspace and synchronize it.
        # First wait a bit for file time stamps to increase enough.
        time.sleep(self.OS_STAT_MTIME_RESOLUTION)
        copyfile(os.path.join(self.local_test_folder_1, 'test.odt'),
                 os.path.join(sync_root, 'test.odt'))
        self.wait_sync()
        self.assertTrue(remote.exists('/test.odt'))
        self.assertEquals(remote.get_content('/test.odt'), 'Some content.')

    def test_concurrent_file_access(self):
        if sys.platform == 'win32':
            raise SkipTest("WIP in https://jira.nuxeo.com/browse/NXDRIVE-170")
        """Test update/deletion of a locally locked file.

        This is to simulate downstream synchronization of a file opened (thus
        locked) by any program under Windows, typically MS Word.
        The file should be blacklisted and not prevent synchronization of other
        pending items.
        Once the file is unlocked and the cooldown period is over it should be
        synchronized.
        """
        # Bind the server and root workspace
        self.engine_1.start()

        # Get local and remote clients
        local = self.local_client_1
        remote = self.remote_document_client_1

        # Create file in the remote root workspace
        remote.make_file('/', 'test_update.docx', 'Some content to update.')
        remote.make_file('/', 'test_delete.docx', 'Some content to delete.')

        # Launch first synchronization
        self.wait_sync()
        self.assertTrue(local.exists('/test_update.docx'))
        self.assertTrue(local.exists('/test_delete.docx'))

        # Open locally synchronized files to lock them and generate a
        # WindowsError when trying to update / delete them
        file1_path = local.get_info('/test_update.docx').filepath
        file1_desc = open(file1_path, 'rb')
        file2_path = local.get_info('/test_delete.docx').filepath
        file2_desc = open(file2_path, 'rb')

        # Update /delete existing remote files and create a new remote file
        # Wait for 1 second to make sure the file's last modification time
        # will be different from the pair state's last remote update time
        time.sleep(self.REMOTE_MODIFICATION_TIME_RESOLUTION)
        remote.update_content('/test_update.docx', 'Updated content.')
        remote.delete('/test_delete.docx')
        remote.make_file('/', 'other.docx', 'Other content.')

        # Synchronize
        self.wait_sync()
        if sys.platform == 'win32':
            # As local file are locked, a WindowsError should occur during the
            # local update process, therefore:
            # - Temporary download file (.part) should be created locally but
            #   not renamed
            # - Opened local files should still exist and not have been
            #   modified
            # - Synchronization should not fail: doc pairs should be
            #   blacklisted and other remote modifications should be locally synchronized
            self.assertTrue(local.exists('/.test_update.docx.nxpart'))
            self.assertTrue(local.exists('/test_update.docx'))
            self.assertEquals(local.get_content('/test_update.docx'),
                              'Some content to update.')
            self.assertTrue(local.exists('/test_delete.docx'))
            self.assertEquals(local.get_content('/test_delete.docx'),
                              'Some content to delete.')
            self.assertTrue(local.exists('/other.docx'))
            self.assertEquals(local.get_content('/other.docx'),
                              'Other content.')

            # Synchronize again
            self.wait_sync()
            # Blacklisted files should be ignored as delay (60 seconds by
            # default) is not expired, nothing should have changed
            self.assertTrue(local.exists('/.test_update.docx.nxpart'))
            self.assertTrue(local.exists('/test_update.docx'))
            self.assertEquals(local.get_content('/test_update.docx'),
                              'Some content to update.')
            self.assertTrue(local.exists('/test_delete.docx'))
            self.assertEquals(local.get_content('/test_delete.docx'),
                              'Some content to delete.')

            # Release file locks by closing them
            file1_desc.close()
            file2_desc.close()
            # Cancel error delay to force retrying synchronization of pairs in error
            self.queue_manager_1.cancel_queued_errors()
            self.wait_sync()

            # Previously blacklisted files should be updated / deleted locally,
            # temporary download file should not be there anymore and there
            # should be no pending items left
            self.assertTrue(local.exists('/test_update.docx'))
            self.assertEquals(local.get_content('/test_update.docx'),
                              'Updated content.')
            self.assertFalse(local.exists('/.test_update.docx.part'))
            self.assertFalse(local.exists('/test_delete.docx'))
        else:
            self.assertTrue(local.exists('/test_update.docx'))
            self.assertEquals(local.get_content('/test_update.docx'),
                              'Updated content.')
            self.assertFalse(local.exists('/.test_update.docx.nxpart'))
            self.assertFalse(local.exists('/test_delete.docx'))
