//˵������

//ϵͳ
#include "stdafx.h"
#include <string>
#include <queue>

//Boost
#define BOOST_PYTHON_STATIC_LIB
#include <boost/python/module.hpp>	//python��װ
#include <boost/python/def.hpp>		//python��װ
#include <boost/python/dict.hpp>	//python��װ
#include <boost/python/list.hpp>	//python��װ
#include <boost/python/object.hpp>	//python��װ
#include <boost/python.hpp>			//python��װ
#include <boost/thread.hpp>			//������е��̹߳���
#include <boost/bind.hpp>			//������е��̹߳���
#include <boost/any.hpp>			//������е�����ʵ��

//API
#include "CITICs_HsT2Hlp.h"

//�����ռ�
using namespace std;
using namespace boost::python;
using namespace boost;


///-------------------------------------------------------------------------------------
///��װ��
///-------------------------------------------------------------------------------------

class CsHsHlp
{
private:
	HSHLPCFGHANDLE cfgHandle;		//����ָ��
	HSHLPHANDLE handle;				//��������ָ��
	thread *task_thread;			//�����߳�ָ�루��python���������ݣ�
	bool active;					//����״̬

public:
	CsHsHlp()
	{
		this->active = false;
	};

	~CsHsHlp()
	{
		this->active = false;
	};

	//------------------------------------------------------------------------
	//������������
	//------------------------------------------------------------------------

	//��ȡ�����ļ�
	int loadConfig(string fileName);

	//��ʼ��
	int init();

	//���ӷ�����
	int connectServer();

	//��ȡ������Ϣ
	string getErrorMsg();

	//��ʼ����������
	int beginParam();

	//���÷����Ĳ����ֶ����ƺ�ֵ
	int setValue(string key, string value);

	//����
	int bizCallAndCommit(int iFuncID);

	//����
	boost::python::list subscribeData(int iFuncID);

	//�Ͽ�������
	int disconnect();

	//�˳�
	int exit();

	//------------------------------------------------------------------------
	//�첽��Ϣ�����߳�
	//------------------------------------------------------------------------

	//�������е���Ϣ������
	void processMsg();

	//------------------------------------------------------------------------
	//Python�м̳еĻص�����
	//------------------------------------------------------------------------
	
	//��Python��������Ϣ�ĺ���
	virtual void onMsg(int type, boost::python::list data, int reqNo, int errorNo, string errorInfo) {};
};
