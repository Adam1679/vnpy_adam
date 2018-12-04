// vncshshlp.cpp : ���� DLL Ӧ�ó���ĵ���������
//

#include "stdafx.h"
#include "vncshshlp.h"

//------------------------------------------------------------------------
//������������
//------------------------------------------------------------------------

//��ȡ�����ļ�
int CsHsHlp::loadConfig(string fileName)
{
	int i = CITICs_HsHlp_LoadConfig(&this->cfgHandle, fileName.c_str());
	return i;
};

//��ʼ��
int CsHsHlp::init()
{
	int i = CITICs_HsHlp_Init(&this->handle, this->cfgHandle);
	return i;
};

//���ӷ�����
int CsHsHlp::connectServer()
{
	int i = CITICs_HsHlp_ConnectServer(this->handle);

	if (this->active == false)
	{
		this->active = true;
		function0<void> f = boost::bind(&CsHsHlp::processMsg, this);
		thread t(f);
		this->task_thread = &t;
	}

	return i;
};

//��ȡ������Ϣ
string CsHsHlp::getErrorMsg()
{
	int i;
	char msg[512];
	CITICs_HsHlp_GetErrorMsg(this->handle, &i, msg);
	string errorMsg = msg;
	return errorMsg;
};

//��ʼ����������
int CsHsHlp::beginParam()
{
	int i = CITICs_HsHlp_BeginParam(this->handle);
	return i;
};

//���÷����Ĳ����ֶ����ƺ�ֵ
int CsHsHlp::setValue(string key, string value)
{
	int i = CITICs_HsHlp_SetValue(this->handle, key.c_str(), value.c_str());
	return i;
};

//�첽����
int CsHsHlp::bizCallAndCommit(int iFuncID)
{
	int i = CITICs_HsHlp_BizCallAndCommit(this->handle, iFuncID, NULL, BIZCALL_ASYNC, NULL);
	return i;
};

//����
boost::python::list CsHsHlp::subscribeData(int iFuncID)
{
	int i = CITICs_HsHlp_BizCallAndCommit(this->handle, iFuncID, NULL, BIZCALL_SUBSCRIBE, NULL);
	
	//����Ϊͬ�����ã���ȡ���صĽ��
	int row = CITICs_HsHlp_GetRowCount(this->handle);		//��ȡmsg�������ж��ٸ���Ӧ��
	int col = CITICs_HsHlp_GetColCount(this->handle);		//��ȡmsg����������Щ�ֶΣ�
	char key[64] = { 0 };
	char value[512] = { 0 };

	boost::python::list data;

	for (int i = 0; i < row; i++)
	{
		if (0 == CITICs_HsHlp_GetNextRow(this->handle))
		{
			dict d;
			for (int j = 0; j < col; j++)
			{
				CITICs_HsHlp_GetColName(this->handle, j, key);
				CITICs_HsHlp_GetValueByIndex(this->handle, j, value);

				string str_key = key;
				string str_value = value;
				d[str_key] = str_value;
			}
			data.append(d);
		}
	}

	return data;
};

//�Ͽ�������
int CsHsHlp::disconnect()
{
	int i = CITICs_HsHlp_DisConnect(this->handle);
	return i;
};

//�˳�
int CsHsHlp::exit()
{
	this->active = false;
	int i = CITICs_HsHlp_Exit(this->handle);
	return i;
};


//------------------------------------------------------------------------
//�첽��Ϣ�����߳�
//------------------------------------------------------------------------

//�������е���Ϣ������
void CsHsHlp::processMsg()
{
	LPMSG_CTRL msgCtrl;			//������Ϣ
	int type = 0;				//��Ϣ����
	int reqNo = 0;				//�첽������
	int errorNo = 0;			//�������
	string errorInfo = "";		//������Ϣ

	int row = 0;				//����
	int col = 0;				//����
	char key[64] = {0};			//��
	char value[512] = {0};		//ֵ

	PyGILState_STATE gil_state;	//GILȫ����

	//��������
	while (this->active)
	{
		//��ʼ��ָ��
		msgCtrl = new MSG_CTRL();

		//��ȡ��Ϣ
		int i = CITICs_HsHlp_QueueGetMsg(this->handle, msgCtrl, -1);

		//��ȡ��Ϣ
		if (msgCtrl->nIssueType)
		{
			type = msgCtrl->nIssueType;
		}
		else
		{
			type = msgCtrl->nFuncID;
		}

		reqNo = msgCtrl->nReqNo;
		errorNo = msgCtrl->nErrorNo;
		errorInfo = msgCtrl->szErrorInfo;

		row = CITICs_HsHlp_GetRowCount(this->handle, msgCtrl);		//��ȡmsg�������ж��ٸ���Ӧ��
		col = CITICs_HsHlp_GetColCount(this->handle, msgCtrl);		//��ȡmsg����������Щ�ֶΣ�

		//�����ֵ䲢���͵�Python��
		gil_state = PyGILState_Ensure();		//����Python����ǰ������GIL

		boost::python::list data;

		for (int i = 0; i < row; i++)
		{	
			if (0 == CITICs_HsHlp_GetNextRow(this->handle, msgCtrl))
			{
				dict d;
				for (int j = 0; j < col; j++)
				{
					CITICs_HsHlp_GetColName(this->handle, j, key, msgCtrl);
					CITICs_HsHlp_GetValueByIndex(this->handle, j, value, msgCtrl);

					string str_key = key;
					string str_value = value;					
					d[str_key] = str_value;
				}
				data.append(d);
			}
		}

		this->onMsg(type, data, reqNo, errorNo, errorInfo);

		PyGILState_Release(gil_state);			//����Python������ɺ��ͷ�GIL

		//�Ӷ���ɾ����Ϣ
		CITICs_HsHlp_QueueEraseMsg(this->handle, msgCtrl);

		//ɾ��ָ��
		delete msgCtrl;
	}
};


///-------------------------------------------------------------------------------------
///Boost.Python��װ
///-------------------------------------------------------------------------------------

struct CsHsHlpWrap : CsHsHlp, wrapper < CsHsHlp >
{
	virtual void onMsg(int type, boost::python::list data, int reqNo, int errorNo, string errorInfo)
	{
		//���µ�try...catch...����ʵ�ֲ�׽python�����д���Ĺ��ܣ���ֹC++ֱ�ӳ���ԭ��δ֪�ı���
		try
		{
			this->get_override("onMsg")(type, data, reqNo, errorNo, errorInfo);
		}
		catch (error_already_set const &)
		{
			PyErr_Print();
		}
	};
};


BOOST_PYTHON_MODULE(vncshshlp)
{
	PyEval_InitThreads();	//����ʱ���У���֤�ȴ���GIL

	class_<CsHsHlpWrap, boost::noncopyable>("CsHsHlp")
		.def("loadConfig", &CsHsHlpWrap::loadConfig)
		.def("init", &CsHsHlpWrap::init)
		.def("connectServer", &CsHsHlpWrap::connectServer)
		.def("getErrorMsg", &CsHsHlpWrap::getErrorMsg)
		.def("beginParam", &CsHsHlpWrap::beginParam)
		.def("setValue", &CsHsHlpWrap::setValue)
		.def("bizCallAndCommit", &CsHsHlpWrap::bizCallAndCommit)
		.def("disconnect", &CsHsHlpWrap::disconnect)
		.def("exit", &CsHsHlpWrap::exit)
		.def("subscribeData", &CsHsHlpWrap::subscribeData)

		.def("onMsg", pure_virtual(&CsHsHlpWrap::onMsg))
		;
};