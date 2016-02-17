$(document).ready(function(){
	var show = function(start,incoming,outgoing){
		var obj = $("#dataAnalysis");
		var chart = obj.highcharts();
		var incomingSeriesData = {
			pointInterval : 3600 * 1000,
			pointStart : start,
			name : '↾',
			data : incoming,
			lineWidth: 1,
			marker: {
                radius: 2
            }
		};
		var outgoingSeriesData = {
				pointInterval : 3600 * 1000,
				pointStart : start,
				name : '⇃',
				data : outgoing,
				lineWidth: 1,
				marker: {
                    radius: 2
                }
			};
		
		if (chart !== undefined) {
			chart.hideLoading();
			chart.series[0].update(incomingSeriesData);
			chart.series[1].update(outgoingSeriesData);
			return
		}
		var startTime = start;
		var plotBands = [];
		var index = 0;
		for ( var i = 0; i < incoming.length;) {
			var startDate = new Date(startTime);
			var endTime = startTime + 3600000;
			if (startDate.getHours()==0) {
				plotBands.push({
					from : startTime,
					to : endTime,
					color : "RGBA(100,30,0,0.07)"
				});
			}
			index++;
			i++;
			startTime = endTime;
		}

		startTime = start;
		
		obj.highcharts({
			title : {
				text : "",
			},
			xAxis : {
				tickWidth: 0,
				type : 'datetime',
				plotBands : plotBands,
				 labels: {
	                    align: 'left',
	                    x: 3,
	                    y: -3
	                }
			},
			yAxis : {
				title : {
					enabled : false,
				},
				lineWidth : 1,
                labels: {
                    align: 'left',
                    x: 3,
                    y: 16,
                },
			},
			tooltip:{
				shared : true,
				formatter:function(){
					var d = new Date(this.x)
					var tmp = ""+(d.getMonth()+1) +"月"+ d.getDate()+"日 "+d.getHours()+"点<br/>";
					for ( var i in this.points) {
						var point = this.points[i];
						tmp += point.series.name+":"+IntToDataCount(point.y)+"<br/>"
					}
					return tmp;
				}
			},
			legend : {
				enabled : false
			},
			plotOptions : {
				area : {
		            marker: {
		                enabled: false,
		                symbol: 'circle',
		                radius: 2,
		                states: {
		                    hover: {
		                        enabled: true
		                    }
		                }
		            }}
			},
			chart : {
				type: 'areaspline'
			},
			credits : {
				enabled : false
			},
			series : [ incomingSeriesData,outgoingSeriesData ]
		});
	}
	
	/** ************************ */

	function echoName(domain,  status, times,index) {
		var statusStr = (status == 1 ? 'close' : 'open')
		f = '<div class="line" status="'+statusStr+'" index="'+index+'">'+
				'<div class="content"><div class="times"><p>'+(times<1000?times:IntToDataCount(times,1000))+'</p></div>'+
				'<div class="domain"><a class="domain_link" target="_blank" href="//'+ domain +'">'+domain+'</a></div></div>' +
				'<div class="optbox">'+
				'<a href="javascript:" class="'+statusStr+'" >'+(status == 1 ? '⌧' : '⇄︎')+'</a>' +
				'<a href="javascript:" class="delete">del</a>' +
				'</div>'+
				'</div>';
		return f;
	}
	window.refreshDomainList = function(){
		proxyapi("domainList",null,function(data){
			var html = "";
			var domainList = data.domainList
			for(var i = 0; i < domainList.length;i++){
				var domain = domainList[i];
				html += echoName(domain.domain,domain.open,domain.connectTimes,i);
			}
			$("#proxyDomainList").html(html);
			$(".close,.open,.delete").click(function(){
				var cls = this.className;
				proxyapi("domainList",{"action":cls,"domain":$(this).parents(".line").find(".domain a").text()},function(){
					refreshDomainList();
				});
			})
		})
	}
	
	refreshDomainList();
	
	$("#newUrlSubmit").click(function(){
		var url = $("#newUrl")[0];
		proxyapi("addDomain",{"url":url.value},function(data){
			var newUrlInfo = $("#newUrlInfo")
			if(data.status == "ok"){
				url.value = "";
				newUrlInfo.text("");
				refreshDomainList();
			}else{
				newUrlInfo.text(url.value+" 错误的URL,末添加")
			}
		});
	})
	
	
	
	/** ************************ */
	
	var domainAnalysisShow = $("#domainAnalysisShow")
	domainAnalysisShow.click(function(){
		var hide = domainAnalysisShow.attr("hide") == "true";
		hide = !hide;
		domainAnalysisShow.attr("hide",hide?"true":"");
		domainAnalysisShow.text(hide?"显示":"隐藏");
		$("#domainAnalysis").css("display",hide?"none":"");
	})
	domainAnalysisShow.click();
	
	var analysisDomain = null;
	var todayAnalysis = function(){
		var startTime = (new Date())/1000-3600*72;
		startTime -= startTime%3600;
		var today = new Date()
		today.setHours(0);
		today.setMinutes(0)
		today.setSeconds(0)
		proxyapi("analysisData",{"startTime":startTime,"todayStartTime":parseInt(today/1000),"domain":(analysisDomain?analysisDomain:"")},function(data){
			var analysisData = data.analysisData;
			show(startTime*1000,analysisData.outgoing,analysisData.incoming);
			
			var html = "";
			$("#domainAnalysisTitle").html('<span>24小时数据流量:</span>'+IntToDataCount(analysisData.countData));
			var list = analysisData.domainDataList;
			
			for(var i = 0; i < list.length;i++){
				var domain = list[i];
				html += '<div class="reusetDomainList">'+
					'<span class="reusetTimes">'+IntToDataCount(domain.dataCount)+'</span>'+
					'<a>'+domain.domain+'</a>'+
					'</div>';
			}
			html += '<div class="reusetDomainList" id="showall">显示全部</div>';
			
			$("#domainAnalysis").html(html);
			function showallbutton(){
				if(analysisDomain)
					$("#showall").show();
				else
					$("#showall").hide();
			}
			$("#domainAnalysis .reusetDomainList").click(function(){
				analysisDomain = $(this).find("a").text();
				showallbutton();
				var obj = $("#dataAnalysis");
				var chart = obj.highcharts();
				chart.showLoading();
				todayAnalysis();
			});
			showallbutton();
			
		});
	};
	setInterval(todayAnalysis,5000);
	todayAnalysis();
})
