%define __prefix /opt
%define __spec_install_post /usr/lib/rpm/brp-compress || :
%define __git https://github.com/FZambia/cyclone-sse.git
%define __descr "exchange-intranet sync daemon"

Name: cyclone_sse
Summary: %{__descr}
Version: %{version}
Release: %{release}
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildRequires: python rpm-build redhat-rpm-config
Requires: python
License: BSD


%description
%{__descr}


%prep
if [ -d %{name} ]; then
    echo "Cleaning out stale build directory" 1>&2
    rm -rf %{name}
fi


%pre
/usr/bin/getent group %{name} || /usr/sbin/groupadd -r %{name}
/usr/bin/getent passwd %{name} || /usr/sbin/useradd -r -d /opt/%{name}/ -s /bin/false %{name} -g %{name}


%postun
/usr/sbin/userdel %{name}


%build
mkdir -p %{name}

git clone %{__git} %{name}/src/
rm -rf %{name}/src/.git*
find %{name}/src/ -type f -name "*.py[co]" -delete

virtualenv --no-site-packages %{name}/env
./%{name}/env/bin/pip install -r %{name}/src/requirements.txt --upgrade
virtualenv --relocatable %{name}/env

# replace builddir path
find %{name}/env/ -type f -exec sed -i "s:%{_builddir}:%{__prefix}:" {} \;


%install
# rpmbuild/BUILD
mkdir -p %{buildroot}%{__prefix}/%{name}
mv %{name} %{buildroot}%{__prefix}/

# hack for lib64
[ -d %{buildroot}%{__prefix}/%{name}/env/lib64 ] && rm -rf %{buildroot}%{__prefix}/%{name}/env/lib64 && ln -sf %{__prefix}/%{name}/env/lib %{buildroot}%{__prefix}/%{name}/env/lib64

# init.d files
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/%{name}/src/deploy/%{name}.initd.sh %{buildroot}%{_initrddir}/%{name}

# configs
mkdir -p %{buildroot}%{_sysconfdir}/%{name}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/%{name}/src/extras/cyclone-sse.conf %{buildroot}%{_sysconfdir}/%{name}/cyclone_sse.conf


# bin
# mkdir -p %{buildroot}%{_bindir}
# ln -s %{__prefix}/%{name}/src/bin/manage.sh %{buildroot}%{_bindir}/%{name}


%post
if [ $1 -gt 1 ]; then
    echo "Upgrade"
    find %{__prefix}/%{name}/ -type f -name "*.py[co]" -delete
    service %{name} restart
else
    echo "Installation completed, now edit config file and then start service"
fi


%clean
rm -rf %{buildroot}


%preun
find %{__prefix}/%{name}/ -type f -name "*.py[co]" -delete


%files
%defattr(-,root,root)
%{_initrddir}/%{name}
%{__prefix}/%{name}/
%config(noreplace) %{_sysconfdir}/%{name}/cyclone_sse.conf

