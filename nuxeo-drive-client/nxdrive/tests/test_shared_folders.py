from nxdrive.tests.common import IntegrationTestCase
from nxdrive.client import RemoteDocumentClient
from nxdrive.client import LocalClient
from nose.plugins.skip import SkipTest


class TestSharedFolders(IntegrationTestCase):

    def test_move_sync_root_child_to_user_workspace(self):
        raise SkipTest("WIP in https://jira.nuxeo.com/browse/NXDRIVE-170")
        """See https://jira.nuxeo.com/browse/NXP-14870"""

        admin_remote_client = self.root_remote_client
        user1_workspace_path = ('/default-domain/UserWorkspaces/'
                                'nuxeoDriveTestUser-user-1')
        try:
            # Get remote  and local clients
            remote_user1 = RemoteDocumentClient(
                self.nuxeo_url, self.user_1, u'nxdrive-test-device-1',
                self.version, password=self.password_1,
                upload_tmp_dir=self.upload_tmp_dir)
            remote_user2 = RemoteDocumentClient(
                self.nuxeo_url, self.user_2, u'nxdrive-test-device-2',
                self.version, password=self.password_2,
                upload_tmp_dir=self.upload_tmp_dir)
            local_user2 = LocalClient(self.local_nxdrive_folder_2)

            # Make sure personal workspace is created for user1
            remote_user1.make_file_in_user_workspace('File in user workspace',
                                                     filename='UWFile.txt')

            # As user1 register personal workspace as a sync root
            remote_user1.register_as_root(user1_workspace_path)

            # As user1 create a parent folder in user1's personal workspace
            remote_user1.make_folder(user1_workspace_path, 'Parent')

            # As user1 grant Everything permission to user2 on parent folder
            parent_folder_path = user1_workspace_path + '/Parent'
            op_input = "doc:" + parent_folder_path
            admin_remote_client.execute("Document.SetACE",
                op_input=op_input,
                user="nuxeoDriveTestUser_user_2",
                permission="Everything",
                grant="true")

            # As user1 create a child folder in parent folder
            remote_user1.make_folder(parent_folder_path, 'Child')

            # As user2 register parent folder as a sync root
            remote_user2.register_as_root(parent_folder_path)

            # Bind server for user2
            ctl_2 = self.controller_2
            ctl_2.bind_server(self.local_nxdrive_folder_2, self.nuxeo_url,
                            self.user_2, self.password_2)

            # Launch first synchronization
            syn_2 = ctl_2.synchronizer
            self._synchronize(syn_2)

            # Check locally synchronized content
            self.assertEquals(len(local_user2.get_children_info('/')), 1)
            self.assertTrue(local_user2.exists('/Parent'))
            self.assertTrue(local_user2.exists('/Parent/Child'))

            # As user1 move child folder to user1's personal workspace
            remote_user1.move(parent_folder_path + '/Child',
                              user1_workspace_path)

            # Synchronize
            self._synchronize(syn_2)

            # Check locally synchronized content
            self.assertFalse(local_user2.exists('/Parent/Child'))

        finally:
            # Cleanup user1 personal workspace
            if admin_remote_client.exists(user1_workspace_path):
                admin_remote_client.delete(user1_workspace_path,
                                           use_trash=False)
