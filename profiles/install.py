##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import os
from os.path import sep
import pkg_resources
import sys
import zc.buildout
import zc.recipe.egg
import hashlib
import ConfigParser


class Recipe:

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    self.cron_d = self.installCrond()
    ca_conf = self.installCertificateAuthority()

    key, certificate = self.requestCertificate('Cloudooo')

    cloudooo_paster = os.path.join(self.bin_directory, 'cloudooo_paster')
    ooo_paster = self.options['ooo_paster']
    if os.path.lexists(cloudooo_paster):
      if not os.readlink(cloudooo_paster) != ooo_paster:
        os.unlink(cloudooo_paster)
    if not os.path.lexists(cloudooo_paster):
      os.symlink(ooo_paster, cloudooo_paster)
    self.options['cloudooo_paster'] = cloudooo_paster

    conversion_server_conf = self.installConversionServer(
        self.getLocalIPv4Address(), 23000, 23060)

    stunnel_conf = self.installStunnel(
        self.getGlobalIPv6Address(),
        conversion_server_conf['conversion_server_ip'],
        23000, conversion_server_conf['conversion_server_port'],
        certificate, key, ca_conf['ca_crl'],
        ca_conf['certificate_authority_path'])

    runCloudoooUnitTest = os.path.join(self.bin_directory, 'runCloudoooUnitTest')
    runUnitTest = self.options['runUnitTest_binary']
    if os.path.lexists(runCloudoooUnitTest):
      if not os.readlink(runCloudoooUnitTest) != runUnitTest:
        os.unlink(runCloudoooUnitTest)
    if not os.path.lexists(runCloudoooUnitTest):
      os.symlink(runUnitTest, runCloudoooUnitTest)
    self.path_list.append(runCloudoooUnitTest)

    self.linkBinary()
    self.setConnectionDict(dict(
          site_url="https://[%s]:%s/" % (stunnel_conf['public_ip'],
                                        stunnel_conf['public_port']),
        ))
    return self.path_list

  def linkBinary(self):
    """Links binaries to instance's bin directory for easier exposal"""
    for linkline in self.options.get('link_binary_list', '').splitlines():
      if not linkline:
        continue
      target = linkline.split()
      if len(target) == 1:
        target = target[0]
        path, linkname = os.path.split(target)
      else:
        linkname = target[1]
        target = target[0]
      link = os.path.join(self.bin_directory, linkname)
      if os.path.lexists(link):
        if not os.path.islink(link):
          raise zc.buildout.UserError(
              'Target link already %r exists but it is not link' % link)
        os.unlink(link)
      os.symlink(target, link)
      self.logger.debug('Created link %r -> %r' % (link, target))
      self.path_list.append(link)

  def installConversionServer(self, ip, port, openoffice_port):
    name = 'conversion_server'
    working_directory = self.createDataDirectory(name)
    conversion_server_dict = dict(
      working_path=working_directory,
      uno_path=self.options['ooo_uno_path'],
      office_binary_path=self.options['ooo_binary_path'],
      ip=ip,
      port=port,
      openoffice_port=openoffice_port,
      openoffice_host=ip,
      PATH=':'.join([os.environ['PATH'], self.bin_directory])
    )
    for env_line in self.options['environment'].splitlines():
      env_line = env_line.strip()
      if not env_line:
        continue
      if '=' in env_line:
        env_key, env_value = env_line.split('=')
        conversion_server_dict[env_key.strip()] = env_value.strip()
      else:
        raise zc.buildout.UserError('Line %r in environment parameter is '
            'incorrect' % env_line)
    config_file = self.createConfigurationFile(name + '.cfg',
        self.substituteTemplate(pkg_resources.resource_filename(__name__, 'template/cloudooo.cfg.in'),
          conversion_server_dict))
    self.path_list.append(config_file)
    self.path_list.extend(zc.buildout.easy_install.scripts([(name,
      'slapos.recipe.librecipe.execute',
      'execute_with_signal_translation')], self.ws,
      sys.executable, self.wrapper_directory,
      arguments=[self.options['cloudooo_paster'].strip(), 'serve', '--log-file',
      '%s/%s'%(self.log_directory, 'cloudooo.log'),config_file]))
    return {
      name + '_conf': config_file,
      name + '_port': conversion_server_dict['port'],
      name + '_ip': conversion_server_dict['ip']
      }
